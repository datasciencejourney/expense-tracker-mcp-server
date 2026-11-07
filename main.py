from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")

CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

app = FastAPI(title="Expense Tracker API")
mcp = FastMCP("Expense Tracker")

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
    amount: float
    category: str
    subcategory: str | None = ""
    note: str | None = ""

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

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Return the categories JSON file."""
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run()