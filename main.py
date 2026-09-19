from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from typing import Optional
import os
import asyncio
import aiosqlite
import tempfile

mcp = FastMCP("ExpenseTracker")

# Writable location: defaults to the OS temp dir (works on FastMCP Cloud's
# read-only/ephemeral container filesystem). Override with an env var if you
# later attach persistent storage.
DATA_DIR = os.environ.get("EXPENSE_TRACKER_DATA_DIR", tempfile.gettempdir())
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")


def current_user_id() -> str:
    """Identifies the caller so each person's data stays isolated.

    Over HTTP with auth enabled (e.g. FastMCP Cloud), this pulls the
    identity from the validated bearer token. In STDIO/local mode there's
    no OAuth handshake at all, so we fall back to a fixed local user --
    this keeps `fastmcp install claude-desktop main.py` working exactly
    as it did before, since that's inherently single-user anyway.
    """
    token = get_access_token()
    if token is None:
        return "local_user"
    return token.claims.get("email") or token.claims.get("sub") or "unknown_user"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'local_user',
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            note TEXT DEFAULT '',
            type TEXT NOT NULL DEFAULT 'debit'
            )
        """)

        # Migrate older databases that don't have these columns yet
        cur = await c.execute("PRAGMA table_info(expenses)")
        cols = [row[1] for row in await cur.fetchall()]
        if "type" not in cols:
            await c.execute(
                "ALTER TABLE expenses ADD COLUMN type TEXT NOT NULL DEFAULT 'debit'")
        if "user_id" not in cols:
            await c.execute(
                "ALTER TABLE expenses ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local_user'")

        await c.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
            user_id TEXT NOT NULL DEFAULT 'local_user',
            category TEXT NOT NULL,
            month TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            PRIMARY KEY (user_id, category, month)
            )
        """)

        # Migrate older budgets tables (previously keyed on category+month only)
        cur = await c.execute("PRAGMA table_info(budgets)")
        budget_cols = [row[1] for row in await cur.fetchall()]
        if "user_id" not in budget_cols:
            await c.execute(
                "ALTER TABLE budgets ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local_user'")

        await c.commit()


def _run_init_db():
    # FastMCP Cloud doesn't run the __main__ block, so initialize the DB
    # at import time instead -- this guarantees the tables exist before any
    # tool is called, regardless of how the server is launched.
    try:
        asyncio.run(init_db())
    except RuntimeError:
        # A loop is already running in this hosting environment (e.g. some
        # ASGI setups start one before importing the app) -- schedule the
        # init on it instead of trying to start a second one.
        loop = asyncio.get_event_loop()
        loop.create_task(init_db())


_run_init_db()


@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = "") -> dict:
    '''Add a new expense (debit) entry to the database.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "INSERT INTO expenses(user_id, date, amount, category, subcategory, note, type) VALUES (?,?,?,?,?,?,?)",
            (user_id, date, amount, category, subcategory, note, "debit")
        )
        await c.commit()
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
async def list_expenses(start_date: str, end_date: str) -> list[dict]:
    '''List expense entries within an inclusive date range.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (user_id, start_date, end_date)
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


@mcp.tool()
async def summarize_expenses(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    '''Summarize expenses (debits only) by category, optionally within a date range.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        base_query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE type = 'debit' AND user_id = ?
        """
        params = [user_id]
        if start_date and end_date:
            base_query += " AND date BETWEEN ? AND ?"
            params += [start_date, end_date]
        base_query += " GROUP BY category ORDER BY total DESC"

        cur = await c.execute(base_query, params)
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        by_category = [dict(zip(cols, r)) for r in rows]

        grand_total = sum(row["total"] for row in by_category)
        total_count = sum(row["count"] for row in by_category)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "grand_total": grand_total,
            "total_entries": total_count,
            "by_category": by_category
        }


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Plain file read (no DB involved) -- reads fresh each time so you can
    # edit the file without restarting.
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


# EDIT Expense tool

@mcp.tool()
async def edit_expense(
    id: int,
    date: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    note: Optional[str] = None,
) -> dict:
    '''Edit an existing expense entry. Only the fields provided are updated;
    omitted fields keep their current value.'''
    user_id = current_user_id()
    fields, values = [], []
    for col, val in [("date", date), ("amount", amount), ("category", category),
                     ("subcategory", subcategory), ("note", note)]:
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)

    if not fields:
        return {"status": "error", "message": "No fields provided to update."}

    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            f"UPDATE expenses SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            (*values, id, user_id)
        )
        await c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "id": id, "updated_fields": [f.split(" = ")[0] for f in fields]}


# Delete expense tool
@mcp.tool()
async def delete_expense(id: int) -> dict:
    '''Delete an expense entry by its id.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?", (id, user_id))
        await c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "id": id, "message": "Expense deleted."}


# credit expense tool--to add the credit

@mcp.tool()
async def credit_expense(date: str, amount: float, category: str = "Income", subcategory: str = "", note: str = "") -> dict:
    '''Record a credit (income, refund, etc.) rather than a spend.
    Stored in the same table but tagged as type='credit'.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "INSERT INTO expenses(user_id, date, amount, category, subcategory, note, type) VALUES (?,?,?,?,?,?,?)",
            (user_id, date, amount, category, subcategory, note, "credit")
        )
        await c.commit()
        return {"status": "ok", "id": cur.lastrowid, "type": "credit"}


@mcp.tool()
async def set_budget(category: str, month: str, limit_amount: float) -> dict:
    '''Set (or update) the monthly spending limit for a category.
    month should be in 'YYYY-MM' format, e.g. '2026-09'.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        await c.execute(
            """
            INSERT INTO budgets(user_id, category, month, limit_amount) VALUES (?,?,?,?)
            ON CONFLICT(user_id, category, month) DO UPDATE SET limit_amount = excluded.limit_amount
            """,
            (user_id, category, month, limit_amount)
        )
        await c.commit()
        return {"status": "ok", "category": category, "month": month, "limit_amount": limit_amount}


@mcp.tool()
async def get_budget_status(month: str) -> list[dict]:
    '''Check spending against budget for each category in a given month ('YYYY-MM').
    Returns limit, actual spend, remaining, and whether it's over budget.'''
    user_id = current_user_id()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "SELECT category, limit_amount FROM budgets WHERE user_id = ? AND month = ?",
            (user_id, month)
        )
        budgets = await cur.fetchall()

        results = []
        for category, limit_amount in budgets:
            spend_cur = await c.execute(
                """
                SELECT COALESCE(SUM(amount), 0) FROM expenses
                WHERE user_id = ? AND category = ? AND type = 'debit' AND date LIKE ?
                """,
                (user_id, category, f"{month}%")
            )
            spent = (await spend_cur.fetchone())[0]

            results.append({
                "category": category,
                "month": month,
                "limit": limit_amount,
                "spent": spent,
                "remaining": limit_amount - spent,
                "over_budget": spent > limit_amount
            })

        return results


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
