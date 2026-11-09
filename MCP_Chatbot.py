import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage

SERVERS = {
    "calculator": {
        "transport": "stdio",
        "command": "/home/lovely/.local/bin/uv",
        "args": [
            "run",
            "fastmcp",
            "run",
            "calculator.py"
        ]
    },
    "expense_tracker": {
        "transport": "streamable_http",
        "url": "https://expense-tracker-connector.fastmcp.app/mcp"
    }
}


async def main():
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    named_tools = {}

    for tool in tools:
        named_tools[tool.name] = tool

    llm = ChatOpenAI(model="gpt-4o")
    llm_with_tools = llm.bind_tools(tools)
    prompt = "What is the product of 12 and 8 using math tool?"

    response = await llm_with_tools.ainvoke([prompt])

    if not getattr(response, "tool_calls", None):
        print("\n LLM Reply: ", response.content)
        return

    tool_messages = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

    result = await named_tools[selected_tool].ainvoke(selected_tool_args)

    tool_messages.append(ToolMessage(content=json.dumps(result), tool_call_id = selected_tool_id))

    final_response = await llm_with_tools.ainvoke([prompt], response, tool_messages)


if __name__ == "__main__":
    asyncio.run(main())