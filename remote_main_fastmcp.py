from fastmcp import FastMCP
import os
import aiosqlite  # Changed: sqlite3 → aiosqlite
import tempfile
# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")
from pydantic import BaseModel
from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")

CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

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

@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str | None = None,
    note: str | None = None
):
    """Add a new expense."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
                  (date, amount, category, subcategory, note))
        c.commit()
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def list_expenses(start_date: str, end_date: str):
    """List expense entries with inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC", (start_date, end_date))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
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

@mcp.tool()
def edit_expense(
    expense_id: int,
    date: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    note: str | None = None
):
    """Update an existing expense by ID."""

    updates = {
        "date": date,
        "amount": amount,
        "category": category,
        "subcategory": subcategory,
        "note": note
    }

    updates = {key: value for key, value in updates.items() if value is not None}

    if not updates:
        return {"status": "error", "message": "No fields provided to update"}

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "SELECT id FROM expenses WHERE id = ?",
            (expense_id,)
        )

        if cur.fetchone() is None:
            return {"status": "error", "message": "Expense not found"}

        set_clause = ", ".join(f"{key} = ?" for key in updates)

        query = f"UPDATE expenses SET {set_clause} WHERE id = ?"

        c.execute(query, (*updates.values(), expense_id))
        c.commit()

    return {
        "status": "success",
        "message": "Expense updated successfully",
        "expense_id": expense_id,
        "updated_fields": list(updates.keys())
    }

@mcp.tool()
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

    return {
        "status": "success",
        "message": "Expense deleted successfully",
        "expense_id": expense_id
    }

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Return the categories JSON file."""
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run()