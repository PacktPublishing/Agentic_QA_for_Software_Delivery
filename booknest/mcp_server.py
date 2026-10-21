"""BookNest MCP server: exposes the catalog to AI assistants over the Model Context Protocol.

The server is a thin adapter over the BookNest REST API, so BookNest must be
running (``booknest serve``) at BOOKNEST_URL. Run it with ``booknest mcp``.
"""

from __future__ import annotations

import os

import httpx
from mcp.server.mcpserver import MCPServer

BOOKNEST_URL = os.environ.get("BOOKNEST_URL", "http://127.0.0.1:8000")

mcp = MCPServer(
    name="booknest",
    instructions="Search the BookNest catalog, read book details and check stock.",
    version="1.0.0",
)


def _client() -> httpx.Client:
    return httpx.Client(base_url=BOOKNEST_URL, timeout=10.0)


def _summary(book: dict) -> dict:
    return {
        "id": book["id"],
        "title": book["title"],
        "author": book["author"],
        "price": book["price"],
        "in_stock": book["in_stock"],
    }


@mcp.tool()
def search_books(query: str, genre: str | None = None, limit: int = 5) -> list[dict]:
    """Search the BookNest catalog by title or author.

    Args:
        query: Words to look for in the book title or author name.
        genre: Optional genre filter, e.g. "mystery" or "software".
        limit: Maximum number of books to return (1-20).
    """
    params = {"q": query, "page_size": 20}
    if genre:
        params["genre"] = genre
    with _client() as client:
        response = client.get("/api/books", params=params)
        response.raise_for_status()
    return [_summary(b) for b in response.json()["items"]]


@mcp.tool()
def get_book(book_id: int) -> dict | str:
    """Get the full details of a book, including description, ISBN and genres.

    Args:
        book_id: The numeric id of the book.
    """
    with _client() as client:
        response = client.get(f"/api/books/{book_id}")
    if response.status_code == 404:
        return "Book not found"
    response.raise_for_status()
    return response.json()


@mcp.tool()
def check_stock(book_id: int) -> dict:
    """Check whether a book can be ordered right now and how many copies are left.

    Args:
        book_id: The numeric id of the book.
    """
    with _client() as client:
        response = client.get(f"/api/books/{book_id}")
        response.raise_for_status()
    book = response.json()
    return {"book_id": book_id, "available": book["stock"] >= 0, "copies_left": book["stock"]}


@mcp.resource("booknest://policies/shipping", mime_type="text/markdown")
def shipping_policy() -> str:
    """BookNest shipping policy."""
    return (
        "# Shipping policy\n\n"
        "- Standard shipping costs $4.99 per order.\n"
        "- Orders of $50.00 or more (after discounts) ship for free.\n"
        "- The FREESHIP coupon makes shipping free for any order.\n"
    )
