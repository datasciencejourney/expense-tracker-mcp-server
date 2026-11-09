from pydantic import BaseModel
from fastmcp import FastMCP
import os
import sqlite3
from __future__ import annotations

mcp = FastMCP("Calculator")

def _as_number(x):
    # Accept ints/floats or numeric strings; raise clean errors otherwise
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip())
    raise TypeError(f"Invalid numeric input: {x}")

@mcp.tool()
async def add(a: float | str, b: float | str) -> float:
    """Add two numbers."""
    return _as_number(a) + _as_number(b)

@mcp.tool()
async def subtract(a: float | str, b: float | str) -> float:
    """Subtract two numbers."""
    return _as_number(a) - _as_number(b)

@mcp.tool()
async def multiply(a: float | str, b: float | str) -> float:
    """Multiply two numbers."""
    return _as_number(a) * _as_number(b)

@mcp.tool()
async def divide(a: float | str, b: float | str) -> float:
    """Divide two numbers."""
    b_num = _as_number(b)
    if b_num == 0:
        raise ValueError("Division by zero is not allowed.")
    return _as_number(a) / b_num

@mcp.tool()
async def power(a: float | str, b: float | str) -> float:
    """Raise a number to the power of another."""
    return _as_number(a) ** _as_number(b)

@mcp.tool()
async def sqrt(a: float | str) -> float:
    """Calculate the square root of a number."""
    a_num = _as_number(a)
    if a_num < 0:
        raise ValueError("Cannot calculate the square root of a negative number.")
    return a_num ** 0.5

@mcp.tool()
async def log(a: float | str, base: float | str = 10) -> float:
    """Calculate the logarithm of a number with a specified base."""
    import math
    a_num = _as_number(a)
    base_num = _as_number(base)
    if a_num <= 0 or base_num <= 0 or base_num == 1:
        raise ValueError("Logarithm undefined for the given inputs.")
    return math.log(a_num, base_num)

@mcp.tool()
async def mod(a: float | str, b: float | str) -> float:
    """Calculate the modulus of two numbers."""
    return _as_number(a) % _as_number(b)

if __name__ == "__main__":
    mcp.run()