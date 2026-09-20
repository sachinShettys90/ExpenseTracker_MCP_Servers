"""
A simple local MCP server exposing basic math tools over stdio.

Run it directly:
    uv run fastmcp run math.py

Or point a client's stdio config at it:
    {
        "command": "uv",
        "args": ["run", "fastmcp", "run", "/absolute/path/to/math.py"]
    }
"""

import math

from fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool()
def add(a: float, b: float) -> float:
    '''Add two numbers.'''
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    '''Subtract b from a.'''
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    '''Multiply two numbers.'''
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    '''Divide a by b. Raises an error if b is zero.'''
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    '''Raise base to the given exponent.'''
    return base ** exponent


@mcp.tool()
def square_root(value: float) -> float:
    '''Return the square root of a non-negative number.'''
    if value < 0:
        raise ValueError("Cannot take the square root of a negative number.")
    return math.sqrt(value)


@mcp.tool()
def modulo(a: float, b: float) -> float:
    '''Return the remainder of a divided by b.'''
    if b == 0:
        raise ValueError("Cannot compute modulo with a divisor of zero.")
    return a % b


@mcp.tool()
def average(numbers: list[float]) -> float:
    '''Return the average (mean) of a list of numbers.'''
    if not numbers:
        raise ValueError("Cannot compute the average of an empty list.")
    return sum(numbers) / len(numbers)


@mcp.tool()
def factorial(n: int) -> int:
    '''Return the factorial of a non-negative integer.'''
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    return math.factorial(n)


@mcp.tool()
def is_prime(n: int) -> bool:
    '''Check whether a given integer is a prime number.'''
    if n < 2:
        return False
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0:
            return False
    return True


if __name__ == "__main__":
    mcp.run()
