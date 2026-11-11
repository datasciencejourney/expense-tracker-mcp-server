import os
import json
import asyncio
import streamlit as st

from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from fastmcp import Client

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)

# --------------------------------------------------
# ENVIRONMENT
# --------------------------------------------------

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")


# --------------------------------------------------
# MCP SERVER CONFIGURATION
# --------------------------------------------------

SERVERS = {
    "mcpServers": {
        "math": {
            "command": "/home/lovely/.local/bin/uv",
            "args": [
                "--directory", "/home/lovely/expense-tracker-mcp-server",
                "run", "fastmcp", "run", "calculator.py",
            ],
        },
        "expense": {
            "url": "https://expense-tracker-connector.fastmcp.app/mcp",
        },
    }
}


# --------------------------------------------------
# SYSTEM PROMPT
# --------------------------------------------------

SYSTEM_PROMPT = """
You are an intelligent assistant with access to two MCP servers.

1. Math server (tools prefixed with math_):
   Use it for mathematical calculations.

2. Expense tracker server (tools prefixed with expense_):
   Use it to add, list, summarize, edit and delete expenses.

IMPORTANT RULES:

- Always use the appropriate tool when a request requires it.
- Never pretend that an operation succeeded without calling its tool.
- For expense updates, preserve fields that the user did not ask to change.
- For deletion, identify the correct expense before deleting it.
- If an expense ID is missing or ambiguous, ask the user for clarification.
- Do not invent database records.
- After executing tools, provide a concise response.
- Do not narrate unnecessary tool execution updates.
"""


# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------

st.set_page_config(
    page_title="MCP Chatbot",
    page_icon="🧰",
    layout="centered",
)

st.title("🧰 MCP Chatbot")
st.caption("Gemini + FastMCP + LangChain")


# --------------------------------------------------
# MCP TOOL DISCOVERY
# --------------------------------------------------

async def discover_tools():
    async with Client(SERVERS) as client:
        mcp_tools = await client.list_tools()

    # Convert MCP tools into plain dicts that Gemini understands
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "parameters": t.input_schema,
        }
        for t in mcp_tools
    ]


# --------------------------------------------------
# CHAT EXECUTION
# --------------------------------------------------

async def process_message(history, llm_with_tools, tool_by_name):

    # First LLM response
    response = await llm_with_tools.ainvoke(history)
    history.append(response)

    # Allow multiple tool-call rounds
    max_rounds = 5

    for _ in range(max_rounds):

        tool_calls = response.tool_calls

        if not tool_calls:
            return response

        for tc in tool_calls:

            tool_name = tc["name"]
            tool_args = tc.get("args") or {}
            tool_id = tc["id"]

            try:
                if tool_name not in tool_by_name:
                    raise ValueError(f"Unknown tool: {tool_name}")

                async with Client(SERVERS) as client:
                    result = await client.call_tool(tool_name, tool_args)

                if result.data is not None:
                    payload = result.data
                else:
                    payload = [
                        b.text for b in result.content
                        if hasattr(b, "text")
                    ]

                result_content = json.dumps(
                    payload,
                    default=str,
                    ensure_ascii=False,
                )

            except Exception as e:
                result_content = json.dumps({
                    "status": "error",
                    "message": str(e),
                })

            history.append(
                ToolMessage(
                    content=result_content,
                    tool_call_id=tool_id,
                )
            )

        # Send tool results back to Gemini
        response = await llm_with_tools.ainvoke(history)
        history.append(response)

    return response


# --------------------------------------------------
# INITIALIZE APPLICATION
# --------------------------------------------------

if "initialized" not in st.session_state:

    with st.spinner("Connecting to MCP servers..."):

        # Initialize Gemini (check this model name exists in AI Studio)
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2,
        )

        # Discover tools from both MCP servers (30s timeout)
        tools = asyncio.run(
            asyncio.wait_for(discover_tools(), timeout=30)
        )

        # Create tool lookup
        tool_by_name = {
            tool["name"]: tool
            for tool in tools
        }

        # Bind MCP tools to Gemini
        llm_with_tools = llm.bind_tools(tools)

        # Save in Streamlit session
        st.session_state.llm = llm
        st.session_state.tools = tools
        st.session_state.tool_by_name = tool_by_name
        st.session_state.llm_with_tools = llm_with_tools

        st.session_state.history = [
            SystemMessage(content=SYSTEM_PROMPT)
        ]

        st.session_state.initialized = True

    st.success(f"Connected! Discovered {len(tools)} MCP tools.")


# --------------------------------------------------
# DISPLAY AVAILABLE TOOLS
# --------------------------------------------------

with st.sidebar:

    st.subheader("Connected MCP Tools")

    for tool in st.session_state.tools:
        st.write(f"🔧 {tool['name']}")

    st.divider()

    if st.button("Clear Chat", use_container_width=True):

        st.session_state.history = [
            SystemMessage(content=SYSTEM_PROMPT)
        ]

        st.rerun()


# --------------------------------------------------
# RENDER CHAT HISTORY
# --------------------------------------------------

for msg in st.session_state.history:

    if isinstance(msg, HumanMessage):

        with st.chat_message("user"):
            st.markdown(msg.content)

    elif isinstance(msg, AIMessage):

        # Hide intermediate tool-call messages
        if msg.tool_calls:
            continue

        with st.chat_message("assistant"):
            st.markdown(msg.content or "")


# --------------------------------------------------
# CHAT INPUT
# --------------------------------------------------

user_text = st.chat_input("Ask something...")

if user_text:

    with st.chat_message("user"):
        st.markdown(user_text)

    st.session_state.history.append(
        HumanMessage(content=user_text)
    )

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            try:
                final_response = asyncio.run(
                    process_message(
                        st.session_state.history,
                        st.session_state.llm_with_tools,
                        st.session_state.tool_by_name,
                    )
                )

                st.markdown(final_response.content or "Done.")

            except Exception as e:
                st.error(f"Error: {str(e)}")