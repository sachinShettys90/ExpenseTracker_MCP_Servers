import asyncio
import json

from dotenv import load_dotenv
from fastmcp import ClientGroup
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from langchain.mcp import MCPAdapter
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI

load_dotenv()

group = ClientGroup(
    {
        "math": Client(
            StdioTransport(
                command="C:\\Users\\Sachin S\\.local\\bin\\uv.exe",
                args=[
                    "run",
                    "fastmcp",
                    "run",
                    r"D:\VSCode_ExpenseTracker_MCP_Servers\MCPClientDemo\math_localserver.py",
                ],
            )
        ),
        "expense": Client(
            "https://expense-tracker-sachin-mcp-serv.fastmcp.app/mcp",
            auth="oauth",  # your server enforces bearer-token auth; this drives the OAuth flow
        )
    }
)


async def main():
    async with MCPAdapter(group) as adapter:
        tools = await adapter.list_tools()

        named_tools = {tool.name: tool for tool in tools}
        print("Available tools:", list(named_tools.keys()))

        llm = ChatOpenAI(model="gpt-5")
        llm_with_tools = llm.bind_tools(tools)

        prompt = "What is 47 times 89, and is the result a prime number?"
        response = await llm_with_tools.ainvoke(prompt)

        if not getattr(response, "tool_calls", None):
            print("\nLLM Reply:", response.content)
            return

        tool_messages = []
        for tc in response.tool_calls:
            selected_tool = tc["name"]
            selected_tool_args = tc.get("args") or {}
            selected_tool_id = tc["id"]

            result = await named_tools[selected_tool].ainvoke(selected_tool_args)
            tool_messages.append(ToolMessage(
                tool_call_id=selected_tool_id, content=json.dumps(result)))

        final_response = await llm_with_tools.ainvoke([prompt, response, *tool_messages])
        print(f"Final response: {final_response.content}")


if __name__ == '__main__':
    asyncio.run(main())


'''
Output 

Available tools: ['math_add', 'math_subtract', 'math_multiply', 'math_divide',
 'math_power', 'math_square_root', 'math_modulo', 'math_average', 'math_factorial',
   'math_is_prime', 'expense_add_expense', 'expense_list_expenses',
 'expense_summarize_expenses', 'expense_edit_expense', 'expense_delete_expense', 
 'expense_credit_expense', 'expense_set_budget', 'expense_get_budget_status']

LLM Reply: 47 × 89 = 4183, and it’s not a prime number (it factors as 47 × 89).
'''
