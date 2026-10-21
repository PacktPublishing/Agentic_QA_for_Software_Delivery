"""Ask the Librarian: BookNest's AI-powered book recommendation feature.

The assistant picks a handful of candidate books from the catalog with a simple
keyword match, then asks Claude to recommend books to the customer.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import anthropic

from booknest.services import DomainError
from booknest.store import Book, Store

MODEL = os.environ.get("BOOKNEST_ASSISTANT_MODEL", "claude-opus-5-5")
MAX_CANDIDATES = 8

SYSTEM_PROMPT = """You are the friendly librarian of BookNest, an online bookstore.
Help customers find books they will love. Be warm and concise (under 150 words).
Use the catalog excerpt below to make your recommendations."""


@dataclass
class Answer:
    text: str
    book_ids: list[int]


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2}


def candidate_books(store: Store, question: str) -> list[Book]:
    """Rank books by how many words they share with the question."""
    words = _words(question)
    scored = []
    for book in store.books.values():
        haystack = _words(f"{book.title} {book.author} {' '.join(book.genres)} {book.description}")
        scored.append((len(words & haystack), book.id, book))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [book for _, _, book in scored[:MAX_CANDIDATES]]


def ask(store: Store, question: str, client: anthropic.Anthropic | None = None) -> Answer:
    books = candidate_books(store, question)
    catalog = [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "price": str(b.price),
            "genres": b.genres,
            "description": b.description,
        }
        for b in books
    ]
    if client is None:
        try:
            client = anthropic.Anthropic()
        except anthropic.AnthropicError as exc:  # no credentials could be resolved
            raise DomainError(503, "The librarian is unavailable: no API key configured") from exc
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=f"{SYSTEM_PROMPT}\n\nCatalog excerpt:\n{json.dumps(catalog, indent=2)}",
            messages=[{"role": "user", "content": question}],
        )
    except anthropic.AuthenticationError as exc:
        raise DomainError(503, "The librarian is unavailable: invalid API key") from exc
    except (anthropic.APIConnectionError, anthropic.RateLimitError) as exc:
        raise DomainError(503, "The librarian is unavailable right now") from exc

    if response.stop_reason == "refusal":
        text = "Sorry, I can't help with that request. Can I help you find a book instead?"
    else:
        text = "".join(block.text for block in response.content if block.type == "text").strip()
    return Answer(text=text, book_ids=[b.id for b in books])
