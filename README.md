# Smart Personal Finance API

An MCP server that lets you track expenses, budgets, and income directly through natural-language chat with Claude (or any MCP-compatible client) — no spreadsheet required.

**🚀 Live server (hosted on FastMCP Cloud):**
```
https://expense-tracker-sachin-mcp-serv.fastmcp.app/mcp
```

**📂 Source code:** https://github.com/sachinShettys90/ExpenseTracker_MCP_Servers

---

## Tech Stack

- **[FastMCP](https://gofastmcp.com)** (Python) — MCP server framework, tools + resources
- **Asynchronous end-to-end** — every DB-backed tool is `async def`, using **[aiosqlite](https://github.com/omnilib/aiosqlite)** instead of blocking `sqlite3` calls. This means concurrent tool calls (e.g. multiple users hitting the server at once) don't block each other while a query is running — the event loop stays free to handle other requests in the meantime.
- **SQLite** — lightweight storage for expenses and budgets
- **Fixed category taxonomy** — `categories.json` exposed as an MCP resource, so the model classifies every expense against a known schema instead of inventing categories on the fly
- **Deployed on FastMCP Cloud** — accessible as a remote MCP server over HTTP, with bearer-token authentication

---

## Try it yourself

You don't need to run anything locally — connect straight to the hosted server above.

> ⚠️ **Note:** This URL is an MCP protocol endpoint, not a webpage. Opening it directly in a browser will show a `Bearer token required` JSON error — that's expected. You need to connect through an actual MCP client (see below), which handles the protocol handshake and authentication for you.

### Claude Desktop / Claude.ai (Custom Connector)

1. Go to **Settings → Connectors → Add custom connector**.
2. Paste in the server URL:
   ```
   https://expense-tracker-sachin-mcp-serv.fastmcp.app/mcp
   ```
3. Save, then start a new chat and try one of the example prompts below.

### Any other MCP client (Cursor, Windsurf, etc.)

Add it as a remote MCP server using the same URL:
```json
{
  "mcpServers": {
    "expense-tracker": {
      "url": "https://expense-tracker-sachin-mcp-serv.fastmcp.app/mcp"
    }
  }
}
```

### MCP Inspector (for exploring tools/schemas)

```bash
npx @modelcontextprotocol/inspector
```
Then connect to `https://expense-tracker-sachin-mcp-serv.fastmcp.app/mcp` as a remote server.

> **Note:** The hosted server uses temporary storage, so data may reset periodically — it's meant for demoing the tools, not as your permanent ledger. Run it locally (see below) if you want persistent data.

---

## I. ExpenseTracker MCP Server

Run the server locally in different modes:

```bash
uv run fastmcp dev inspector main.py            # Run in the MCP Inspector (for interactive testing)
uv run fastmcp install claude-desktop main.py   # Install as a local MCP server for Claude Desktop
uv run python main.py                           # Run directly as an HTTP server (0.0.0.0:8000)
```

> **Note:** When you type expense-related messages in Claude, it will automatically create `expenses.db` (if it doesn't exist) and add data to it.

### Adding expenses

```
add an expense - groceries yesterday for Rs 500
add an expense - cab ride to Bangalore to Hassan last saturday, fare was 900Rs
```

### Listing expenses

**Query:**
```
list my expenses from september 1st week and also write the summary
```

**Output:**

| Date  | Category         | Note                    | Amount |
|-------|-------------------|--------------------------|--------|
| Sep 1 | Groceries         | DMart                    | ₹1,600 |
| Sep 3 | Travel            | Train ticket to Mysore   | ₹450   |
| Sep 5 | Health & Fitness  | Medicines from pharmacy  | ₹320   |
| Sep 7 | Food              | Swiggy order             | ₹540   |

### Summarizing expenses

**Query:**
```
can you summarise my total expense from Aug 5th to Aug 30th
```

**Output:**

| Category          | Total    | Entries |
|--------------------|----------|---------|
| Housing            | ₹15,000  | 1       |
| Food               | ₹2,480   | 3       |
| Shopping           | ₹2,350   | 1       |
| Health & Fitness   | ₹2,000   | 1       |
| Travel             | ₹1,720   | 2       |
| Utilities          | ₹1,398   | 2       |
| Entertainment      | ₹800     | 1       |

### Editing an expense

**Query:**
```
Change my food expense from Sep 23 to Rs 900
```

**Output:**
```
Done — the Sep 23 Food expense ("Dinner date") is updated from ₹1,800 to ₹900.
```

### Deleting an expense

**Query:**
```
Delete my Sep 23 dinner expense
```

**Output:**
```
Deleted — the Sep 23 Food expense ("Dinner date", ₹900, id 41) has been removed.
```

### Credit expense

**Query:**
```
I received a mutual fund payout of Rs 5000 on Sep 20, add as credit
```

**Output:**
```
Added — ₹5,000 credit on Sep 20, categorized as Investment, note "Mutual fund payout" (entry id 36).
```

### Budgets

**Q1:**
```
Set my budget for food this month to Rs 8000
```
**Output:** `Set — Food budget for September 2026 is now ₹8,000.`

**Q2:**
```
What's the current expense for September month in food category
```
**Output:**
```
You've spent ₹1,440 on Food this September — well under your ₹8,000 budget, with ₹6,560 remaining.
```

**Q3:**
```
How am I doing against my budget for September?
```
**Output:**
```
That's the only budget you've set so far — Food — so here's the full picture:

Food — September 2026
Budget: ₹8,000
Spent: ₹1,440
Remaining: ₹6,560
Status: well under budget ✅
```

### Categories

`categories.json` defines the fixed set of valid categories and subcategories (e.g. `food`, `transport`, `housing`, `utilities`, `health`, `travel`, `subscriptions`, etc.). This is exposed to Claude as an MCP resource so that new expenses are always classified against this known list, instead of the model inventing arbitrary category names on its own.

---

## Engineering Challenges & Solutions

Building and hardening this server surfaced a few real problems that come up when you move a project from "it works on my laptop" to "it works for real, for other people."

### 1. The server kept forgetting data after updates

**Challenge:** When I redeployed the server online, it sometimes lost all the saved expenses. That's because the cloud platform gives each deployment a fresh, temporary storage space — nothing saved there sticks around permanently unless you point it somewhere specifically meant to last.

**Solution:** I made the app save to a proper temporary storage location the platform actually supports, and set it up so I can easily switch to permanent storage later without rewriting the code.

### 2. The tools weren't strict about what data they'd accept

**Challenge:** When I tested the server with a diagnostic tool, it warned me that every single feature (adding an expense, editing one, etc.) would accept literally anything as input — text, numbers, anything — with no rules. That's risky because some apps that talk to this server would get confused by that flexibility.

**Solution:** I clearly stated what type of value each field expects (a number for amount, text for a category, and so on), so each tool now only accepts sensible input.

### 3. The app could freeze up when multiple people used it at once

**Challenge:** Originally, every time the app talked to the database, it would "block" — meaning nothing else could happen until that one request finished. That's fine with one person, but if several people used the app at the same time, everyone would end up waiting in line, even for tiny actions.

**Solution:** I rewrote the database logic to work asynchronously, meaning the app can now handle multiple requests at the same time instead of making everyone wait their turn.

### 4. Everyone's expenses were mixed together

**Challenge:** This was the biggest one. The app had no way of knowing *who* an expense belonged to — so if two different people used the server, their expenses (and even their budgets) would all show up together in one shared list. Even worse, one person could accidentally edit or delete someone else's expense.

**Solution:** I fixed this by having the app recognize *who* is logged in each time someone uses it, and making sure every action — adding, viewing, editing, deleting — only ever touches that person's own data, never anyone else's.

One extra detail worth mentioning: this "who's logged in" check only works when the app is used online through the hosted version, since that's the only place where people actually log in. When running it privately on my own computer, there's no login step at all, so I made sure that mode still works fine on its own, treating it as a single, personal user.

---

## II. FastAPI Version

```bash
uv run uvicorn ExpenseTracker_with_FastAPI:app --reload   # Run the FastAPI application
```

### Expense Tracker API Endpoints

| Method | Endpoint               | Description                    |
|--------|-------------------------|---------------------------------|
| GET    | `/expenses`             | List expenses                  |
| POST   | `/expenses`             | Add a new expense               |
| PUT    | `/expenses/{id}`        | Edit an existing expense       |
| DELETE | `/expenses/{id}`        | Delete an expense              |
| POST   | `/credits`              | Add a credit entry             |
| GET    | `/expenses/summary`     | Get category-wise summary      |
| POST   | `/budgets`              | Set a budget for a category    |
| GET    | `/budgets/{month}`      | Get budget status for a month  |

---

## III. FastAPI → MCP Server (`server.py`)

Wraps the FastAPI application as an MCP server:

```bash
uv run fastmcp dev inspector server.py   # Run the FastAPI app as an MCP server in the Inspector
```