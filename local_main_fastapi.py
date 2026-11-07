from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")

app = FastAPI(title="Expense Tracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            note TEXT DEFAULT ''
        )
        """)

init_db()

class ExpenseCreate(BaseModel):
    date: str
    amount: float = Field(gt=0)
    category: str
    subcategory: str | None = ""
    note: str | None = ""

class ExpenseUpdate(BaseModel):
    date: str | None = None
    amount: float | None = None
    category: str | None = None
    subcategory: str | None = None
    note: str | None = None

@app.post("/expenses")
def add_expense(payload: ExpenseCreate):
    """Add a new expense."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
                  (payload.date, payload.amount, payload.category, payload.subcategory, payload.note))
        c.commit()
        return {"status": "ok", "id": cur.lastrowid}

@app.get("/expenses")
def list_expenses(start_date: str, end_date: str):
    """List expense entries with inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC", (start_date, end_date))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@app.get("/expenses/summarize")
def summarize(start_date: str, end_date: str, category: str = None):
    """summarize expenses by category within an inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) as total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY CATEGORY ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@app.put("/expenses/{expense_id}")
@app.put("/expenses/{expense_id}")
def edit_expense(expense_id: int, payload: ExpenseUpdate):
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No fields provided to update"
        )

    with sqlite3.connect(DB_PATH) as c:
        set_clause = ", ".join(f"{key} = ?" for key in updates)

        cur = c.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?",
            (*updates.values(), expense_id)
        )

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Expense not found"
            )

    return {
        "status": "success",
        "expense_id": expense_id,
        "updated_fields": list(updates.keys())
    }

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    """Delete an expense by its ID."""

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

        c.commit()

        if cur.rowcount == 0:
            return {
                "status": "error",
                "message": "Expense not found"
            }

    if cur.rowcount == 0:
        raise HTTPException(
        status_code=404,
        detail="Expense not found"
    )