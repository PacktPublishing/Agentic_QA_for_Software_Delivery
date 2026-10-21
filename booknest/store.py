"""In-memory data store for BookNest.

BookNest keeps everything in memory so that every test run can start from the
same known state: call ``Store.reset()`` (or ``POST /api/testing/reset``) to
reload the seed data.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock

SEED_FILE = Path(__file__).parent / "seed" / "books.json"


@dataclass
class Book:
    id: int
    title: str
    author: str
    isbn: str
    price: Decimal
    stock: int
    genres: list[str]
    description: str
    published_year: int


@dataclass
class User:
    id: int
    email: str
    name: str
    password_hash: str
    is_admin: bool = False


@dataclass
class Coupon:
    code: str
    kind: str  # "percent" | "free_shipping"
    value: Decimal
    min_subtotal: Decimal
    expires_on: date | None


@dataclass
class Cart:
    lines: dict[int, int] = field(default_factory=dict)  # book_id -> quantity
    coupon_code: str | None = None


@dataclass
class OrderLine:
    book_id: int
    title: str
    unit_price: Decimal
    quantity: int


@dataclass
class Order:
    id: int
    user_id: int
    lines: list[OrderLine]
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal
    coupon_code: str | None
    status: str  # "placed" | "shipped" | "delivered" | "cancelled"
    created_at: datetime


@dataclass
class Review:
    id: int
    book_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, _ = password_hash.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), password_hash)


class Store:
    def __init__(self, seed_file: Path = SEED_FILE) -> None:
        self.seed_file = seed_file
        self.lock = RLock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            seed = json.loads(self.seed_file.read_text())
            self.books: dict[int, Book] = {
                b["id"]: Book(**{**b, "price": Decimal(b["price"])}) for b in seed["books"]
            }
            self.users: dict[int, User] = {
                u["id"]: User(
                    id=u["id"],
                    email=u["email"],
                    name=u["name"],
                    password_hash=hash_password(u["password"]),
                    is_admin=u["is_admin"],
                )
                for u in seed["users"]
            }
            self.coupons: dict[str, Coupon] = {
                c["code"]: Coupon(
                    code=c["code"],
                    kind=c["kind"],
                    value=Decimal(c["value"]),
                    min_subtotal=Decimal(c["min_subtotal"]),
                    expires_on=date.fromisoformat(c["expires_on"]) if c["expires_on"] else None,
                )
                for c in seed["coupons"]
            }
            self.revoked_jtis: set[str] = set()
            self.carts: dict[int, Cart] = {}
            self.orders: dict[int, Order] = {}
            self.reviews: dict[int, Review] = {}
            self._next_ids = {
                "user": max(self.users) + 1,
                "order": 1001,
                "review": 1,
            }

    def next_id(self, kind: str) -> int:
        with self.lock:
            value = self._next_ids[kind]
            self._next_ids[kind] += 1
            return value

    def cart_for(self, user_id: int) -> Cart:
        return self.carts.setdefault(user_id, Cart())
