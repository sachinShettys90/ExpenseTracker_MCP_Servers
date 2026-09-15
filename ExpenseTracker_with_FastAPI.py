from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import sqlite3
import os


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

app = FastAPI(
    title="Expense Tracker API",
    description="REST API for managing expenses, income, and budgets",
    version="1.0.0",
)


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as c:
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

        # Migration for older databases
        cols = [
            row["name"]
            for row in c.execute("PRAGMA table_info(expenses)")
        ]

        if "type" not in cols:
            c.execute("""
                ALTER TABLE expenses
                ADD COLUMN type TEXT NOT NULL DEFAULT 'debit'
            """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
                category TEXT NOT NULL,
                month TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                PRIMARY KEY (category, month)
            )
        """)


@app.on_event("startup")
def startup():
    init_db()


# ---------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------

class ExpenseCreate(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    amount: float = Field(..., gt=0)
    category: str
    subcategory: str = ""
    note: str = ""


class ExpenseUpdate(BaseModel):
    date: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    note: Optional[str] = None


class CreditCreate(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    amount: float = Field(..., gt=0)
    category: str = "Income"
    subcategory: str = ""
    note: str = ""


class BudgetCreate(BaseModel):
    category: str
    month: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Month in YYYY-MM format"
    )
    limit_amount: float = Field(..., ge=0)


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Expense Tracker API is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------------------------------------------------------
# Expenses
# ---------------------------------------------------------

@app.post("/expenses", status_code=201)
def add_expense(expense: ExpenseCreate):
    with get_db() as c:
        cur = c.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note, type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                expense.date,
                expense.amount,
                expense.category,
                expense.subcategory,
                expense.note,
                "debit"
            )
        )

        return {
            "status": "ok",
            "id": cur.lastrowid,
            "type": "debit"
        }


@app.get("/expenses")
def list_expenses(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD")
):
    with get_db() as c:
        rows = c.execute(
            """
            SELECT
                id,
                date,
                amount,
                category,
                subcategory,
                note,
                type
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (start_date, end_date)
        ).fetchall()

        return [dict(row) for row in rows]


@app.get("/expenses/{expense_id}")
def get_expense(expense_id: int):
    with get_db() as c:
        row = c.execute(
            """
            SELECT
                id,
                date,
                amount,
                category,
                subcategory,
                note,
                type
            FROM expenses
            WHERE id = ?
            """,
            (expense_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No expense found with id {expense_id}."
            )

        return dict(row)


# ---------------------------------------------------------
# Edit expense
# ---------------------------------------------------------

@app.put("/expenses/{expense_id}")
def edit_expense(
    expense_id: int,
    expense: ExpenseUpdate
):
    update_data = expense.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided to update."
        )

    fields = []
    values = []

    allowed_fields = [
        "date",
        "amount",
        "category",
        "subcategory",
        "note"
    ]

    for field in allowed_fields:
        if field in update_data:
            fields.append(f"{field} = ?")
            values.append(update_data[field])

    if not fields:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided to update."
        )

    values.append(expense_id)

    with get_db() as c:
        cur = c.execute(
            f"""
            UPDATE expenses
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No expense found with id {expense_id}."
            )

        return {
            "status": "ok",
            "id": expense_id,
            "updated_fields": list(update_data.keys())
        }


# ---------------------------------------------------------
# Delete expense
# ---------------------------------------------------------

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    with get_db() as c:
        cur = c.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No expense found with id {expense_id}."
            )

        return {
            "status": "ok",
            "id": expense_id,
            "message": "Expense deleted."
        }


# ---------------------------------------------------------
# Credit / Income
# ---------------------------------------------------------

@app.post("/credits", status_code=201)
def add_credit(credit: CreditCreate):
    with get_db() as c:
        cur = c.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note, type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                credit.date,
                credit.amount,
                credit.category,
                credit.subcategory,
                credit.note,
                "credit"
            )
        )

        return {
            "status": "ok",
            "id": cur.lastrowid,
            "type": "credit"
        }


# ---------------------------------------------------------
# Expense summary
# ---------------------------------------------------------

@app.get("/expenses/summary")
def summarize_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    with get_db() as c:

        query = """
            SELECT
                category,
                SUM(amount) AS total,
                COUNT(*) AS count
            FROM expenses
            WHERE type = 'debit'
        """

        params = []

        if start_date and end_date:
            query += " AND date BETWEEN ? AND ?"
            params.extend([start_date, end_date])

        query += """
            GROUP BY category
            ORDER BY total DESC
        """

        rows = c.execute(query, params).fetchall()

        by_category = [dict(row) for row in rows]

        grand_total = sum(
            row["total"] for row in by_category
        )

        total_count = sum(
            row["count"] for row in by_category
        )

        return {
            "start_date": start_date,
            "end_date": end_date,
            "grand_total": grand_total,
            "total_entries": total_count,
            "by_category": by_category
        }


# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------

@app.post("/budgets")
def set_budget(budget: BudgetCreate):
    with get_db() as c:
        c.execute(
            """
            INSERT INTO budgets
            (category, month, limit_amount)
            VALUES (?, ?, ?)
            ON CONFLICT(category, month)
            DO UPDATE SET
                limit_amount = excluded.limit_amount
            """,
            (
                budget.category,
                budget.month,
                budget.limit_amount
            )
        )

        return {
            "status": "ok",
            "category": budget.category,
            "month": budget.month,
            "limit_amount": budget.limit_amount
        }


@app.get("/budgets/{month}")
def get_budget_status(month: str):
    with get_db() as c:

        budgets = c.execute(
            """
            SELECT category, limit_amount
            FROM budgets
            WHERE month = ?
            """,
            (month,)
        ).fetchall()

        results = []

        for budget in budgets:
            category = budget["category"]
            limit_amount = budget["limit_amount"]

            spent = c.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE category = ?
                  AND type = 'debit'
                  AND date LIKE ?
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
