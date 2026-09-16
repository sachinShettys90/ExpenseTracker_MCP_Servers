from fastmcp import FastMCP
import os
import sqlite3
import tempfile

mcp = FastMCP("ExpenseTracker")

# Writable location: defaults to the OS temp dir (works on FastMCP Cloud's
# read-only/ephemeral container filesystem). Override with an env var if you
# later attach persistent storage.
DATA_DIR = os.environ.get("EXPENSE_TRACKER_DATA_DIR", tempfile.gettempdir())
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")


def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            note TEXT DEFAULT '',
            type TEXT NOT NULL DEFAULT 'debit'
            )
        """)

        # Migrate older databases that don't have the 'type' column yet
        cols = [row[1] for row in c.execute("PRAGMA table_info(expenses)")]
        if "type" not in cols:
            c.execute(
                "ALTER TABLE expenses ADD COLUMN type TEXT NOT NULL DEFAULT 'debit'")

        c.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
            category TEXT NOT NULL,
            month TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            PRIMARY KEY (category, month)
            )
        """)


# FastMCP Cloud doesn't run the __main__ block, so initialize the DB
# at import time instead — this guarantees the tables exist before any
# tool is called, regardless of how the server is launched.
init_db()


@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense (debit) entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, type) VALUES (?,?,?,?,?,?)",
            (date, amount, category, subcategory, note, "debit")
        )
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize_expenses(start_date=None, end_date=None):
    '''Summarize expenses (debits only) by category, optionally within a date range.'''
    with sqlite3.connect(DB_PATH) as c:
        base_query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE type = 'debit'
        """
        params = []
        if start_date and end_date:
            base_query += " AND date BETWEEN ? AND ?"
            params = [start_date, end_date]
        base_query += " GROUP BY category ORDER BY total DESC"

        cur = c.execute(base_query, params)
        cols = [d[0] for d in cur.description]
        by_category = [dict(zip(cols, r)) for r in cur.fetchall()]

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
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


# EDIT Expense tool

@mcp.tool()
def edit_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    '''Edit an existing expense entry. Only the fields provided are updated;
    omitted fields keep their current value.'''
    fields, values = [], []
    for col, val in [("date", date), ("amount", amount), ("category", category),
                     ("subcategory", subcategory), ("note", note)]:
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)

    if not fields:
        return {"status": "error", "message": "No fields provided to update."}

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?", (*values, id))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "id": id, "updated_fields": [f.split(" = ")[0] for f in fields]}


# Delete expense tool
@mcp.tool()
def delete_expense(id):
    '''Delete an expense entry by its id.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "id": id, "message": "Expense deleted."}


# credit expense tool--to add the credit

@mcp.tool()
def credit_expense(date, amount, category="Income", subcategory="", note=""):
    '''Record a credit (income, refund, etc.) rather than a spend.
    Stored in the same table but tagged as type='credit'.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, type) VALUES (?,?,?,?,?,?)",
            (date, amount, category, subcategory, note, "credit")
        )
        return {"status": "ok", "id": cur.lastrowid, "type": "credit"}


@mcp.tool()
def set_budget(category, month, limit_amount):
    '''Set (or update) the monthly spending limit for a category.
    month should be in 'YYYY-MM' format, e.g. '2026-09'.'''
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            """
            INSERT INTO budgets(category, month, limit_amount) VALUES (?,?,?)
            ON CONFLICT(category, month) DO UPDATE SET limit_amount = excluded.limit_amount
            """,
            (category, month, limit_amount)
        )
        return {"status": "ok", "category": category, "month": month, "limit_amount": limit_amount}


@mcp.tool()
def get_budget_status(month):
    '''Check spending against budget for each category in a given month ('YYYY-MM').
    Returns limit, actual spend, remaining, and whether it's over budget.'''
    with sqlite3.connect(DB_PATH) as c:
        budgets = c.execute(
            "SELECT category, limit_amount FROM budgets WHERE month = ?", (
                month,)
        ).fetchall()

        results = []
        for category, limit_amount in budgets:
            spent = c.execute(
                """
                SELECT COALESCE(SUM(amount), 0) FROM expenses
                WHERE category = ? AND type = 'debit' AND date LIKE ?
                """,
                (category, f"{month}%")
            ).fetchone()[0]

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
