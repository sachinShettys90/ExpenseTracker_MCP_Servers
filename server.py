from fastmcp import FastMCP
from ExpenseTracker_with_FastAPI import app


# Convert FastAPI application to an MCP server
mcp = FastMCP.from_fastapi(
    app=app,
    name="Expense Tracker Server",
)


if __name__ == "__main__":
    mcp.run()
