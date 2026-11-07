
import asyncio
import os
from pathlib import Path

import aiosqlite
from fastmcp import FastMCP


DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("Expense Tracker")


# Initialize database
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        await db.commit()


# Add expense
@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str | None = None,
    note: str | None = None
):
    """Add a new expense."""

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory or "", note or "")
        ) as cursor:
            expense_id = cursor.lastrowid

        await db.commit()

    return {"status": "success", "id": expense_id}


# List expenses
@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    """List expenses within an inclusive date range."""

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

    return [dict(zip(columns, row)) for row in rows]


# Summarize expenses
@mcp.tool()
async def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None
):
    """Summarize expenses by category within a date range."""

    query = """
        SELECT category, SUM(amount) AS total_amount
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """

    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY category ASC"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

    return [dict(zip(columns, row)) for row in rows]


# Edit expense
@mcp.tool()
async def edit_expense(
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

    updates = {
        key: value
        for key, value in updates.items()
        if value is not None
    }

    if not updates:
        return {
            "status": "error",
            "message": "No fields provided to update"
        }

    set_clause = ", ".join(
        f"{key} = ?" for key in updates
    )

    query = f"UPDATE expenses SET {set_clause} WHERE id = ?"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            query,
            (*updates.values(), expense_id)
        ) as cursor:
            if cursor.rowcount == 0:
                return {
                    "status": "error",
                    "message": "Expense not found"
                }

        await db.commit()

    return {
        "status": "success",
        "message": "Expense updated successfully",
        "expense_id": expense_id,
        "updated_fields": list(updates.keys())
    }


# Delete expense
@mcp.tool()
async def delete_expense(expense_id: int):
    """Delete an expense by its ID."""

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        ) as cursor:
            deleted = cursor.rowcount

        if deleted == 0:
            return {
                "status": "error",
                "message": "Expense not found"
            }

        await db.commit()

    return {
        "status": "success",
        "message": "Expense deleted successfully",
        "expense_id": expense_id
    }


# Categories resource
@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
async def categories():
    """Return the categories JSON file."""

    return await asyncio.to_thread(
        Path(CATEGORIES_PATH).read_text,
        encoding="utf-8"
    )


# Start MCP server
if __name__ == "__main__":
    asyncio.run(init_db())

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )
