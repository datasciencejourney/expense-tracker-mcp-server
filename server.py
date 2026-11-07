from fastmcp import FastMCP
from main import app

mcp = FastMCP.from_fastapi(
    app = app,
    name = "Expense Tracker",   
)

if __name__ == "__main__":
    mcp.run()