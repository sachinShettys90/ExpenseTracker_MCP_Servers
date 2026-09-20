# MCP Client Demo — Multi-Server LangChain Agent

A small demo client that connects a single LangChain agent to **two different MCP servers at once** — one running locally over stdio, one hosted remotely over HTTP with OAuth — and lets an LLM pick and call tools from either, transparently.

## What this demonstrates

- Mixing transports in one agent: **stdio** (local subprocess) + **Streamable HTTP** (remote, authenticated)
- Per-server authentication via `ClientGroup`, so only the server that needs auth (`expense`) uses it
- Automatic tool-name prefixing (`math_add`, `expense_add_expense`, etc.) so two servers can never collide on tool names
- A full tool-calling loop: prompt → model picks a tool → tool runs → result fed back → model gives a final answer

## Servers in this demo

| Server | Transport | Auth | Source |
|---|---|---|---|
| `math` | stdio (local subprocess) | none | `math_localserver.py`, run locally via `uv run fastmcp run ...` |
| `expense` | Streamable HTTP | OAuth (bearer token) | Hosted on FastMCP Cloud: `https://expense-tracker-sachin-mcp-serv.fastmcp.app/mcp` |

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) installed and on your `PATH` (or note its full path — see Configuration below)
- An OpenAI API key (this demo uses `ChatOpenAI(model="gpt-5")`)
- `math_localserver.py` present locally (a simple FastMCP server exposing basic math tools: `add`, `subtract`, `multiply`, `divide`, `power`, `square_root`, `modulo`, `average`, `factorial`, `is_prime`)

## Install

```bash
uv add langchain[mcp] langchain-openai python-dotenv fastmcp
```

> **Note:** `langchain.mcp` is currently in beta — importing it raises a `LangChainBetaWarning`. This is expected and harmless.

## Configuration

Create a `.env` file in the same folder as `Client.py`:

```
OPENAI_API_KEY=sk-...
```

In `Client.py`, update the `math` server's `command` and script path to match your machine:

```python
"math": Client(
    StdioTransport(
        command=r"C:\Users\<you>\.local\bin\uv.exe",  # or just "uv" if it's on PATH
        args=[
            "run", "fastmcp", "run",
            r"D:\path\to\your\math_localserver.py",
        ],
    )
),
```

The `expense` server's URL points at a specific hosted deployment — swap it for your own FastMCP Cloud URL if you're running a different instance.

## Run it

```bash
uv run python Client.py
```

On first run, the `expense` server's OAuth flow will open a browser tab asking you to approve access. Tokens are held in memory by default, so you'll need to re-approve on every run unless you configure persistent token storage (see [FastMCP's OAuth token storage docs](https://gofastmcp.com/clients/auth/oauth#token-storage)).

### Example output

```
Available tools: ['math_add', 'math_subtract', 'math_multiply', 'math_divide',
 'math_power', 'math_square_root', 'math_modulo', 'math_average', 'math_factorial',
 'math_is_prime', 'expense_add_expense', 'expense_list_expenses',
 'expense_summarize_expenses', 'expense_edit_expense', 'expense_delete_expense',
 'expense_credit_expense', 'expense_set_budget', 'expense_get_budget_status']

LLM Reply: 47 × 89 = 4183, and it's not a prime number (it factors as 47 × 89).
```

## How it works

1. **`ClientGroup`** wraps two independent `fastmcp.Client` instances — one built from a `StdioTransport` (spawns the local math server as a subprocess), one built from a bare URL string with `auth="oauth"` (FastMCP infers HTTP transport and runs the full OAuth 2.1 flow). `ClientGroup` is the right tool specifically *because* the two servers need different transports and only one needs auth — a plain `MCPConfig` dict can't express per-server credentials.
2. **`MCPAdapter(group)`** is used as an async context manager. Entering it connects to both servers concurrently; `adapter.list_tools()` returns every tool from both, each name prefixed with its server key (`math_`, `expense_`) so there's no ambiguity for the model.
3. **`llm.bind_tools(tools)`** hands the full combined toolset to the model. The model decides which tool(s) to call based on the prompt — it doesn't need to know or care which server a tool lives on.
4. **The manual tool-calling loop** (rather than a prebuilt agent executor) explicitly shows each step: the model's `tool_calls`, invoking the matching tool via `named_tools[...].ainvoke(...)`, wrapping the result in a `ToolMessage`, and sending everything back to the model for a final natural-language answer.

## Known issues / things to watch for

- **Windows file locks during `uv add`/`uv sync`:** if you hit `Access is denied` errors on `.pyd`/`.dll` files during dependency installs, it's usually caused by leftover orphaned Python processes from previous `uv run` invocations (check with `Get-Process python*`) or antivirus real-time scanning (McAfee and Windows Defender have both been observed locking freshly-written compiled extension files on this project). Kill stray Python processes first; add an AV exclusion for the project folder if it persists.
- **`langchain.mcp` is beta** — the API may change in future LangChain releases. If tool signatures or `MCPAdapter`/`ClientGroup` behavior shift, check the [migration guide](https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters) for the current shape.
- **In-memory OAuth tokens** mean every run re-triggers the browser consent flow. Fine for a demo; annoying for repeated local testing — worth setting up a persistent token store if you're iterating frequently.