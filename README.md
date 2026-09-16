# Smart Personal Finance API

## I. ExpenseTracker MCP Server

Run the server in different modes:

```bash
uv run fastmcp dev inspector main.py     # Run in the MCP Inspector (for interactive testing)
uv run fastmcp install claude-desktop main.py   # Install as a local MCP server for Claude Desktop
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