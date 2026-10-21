"""BookNest use cases, shared by the REST API and the web UI."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import jwt

from booknest import pricing
from booknest.store import (
    Book,
    Cart,
    Order,
    OrderLine,
    Review,
    Store,
    User,
    hash_password,
    verify_password,
)

JWT_ALGORITHM = "HS256"
TOKEN_TTL_MINUTES = int(os.environ.get("BOOKNEST_JWT_TTL_MINUTES", "60"))
# Without BOOKNEST_JWT_SECRET a random per-process key is used, so tokens die on restart.
_FALLBACK_SECRET = secrets.token_urlsafe(32)


def _jwt_secret() -> str:
    return os.environ.get("BOOKNEST_JWT_SECRET") or _FALLBACK_SECRET


class DomainError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def today() -> date:
    return datetime.now(UTC).date()


# --- Accounts -------------------------------------------------------------------


def register(store: Store, email: str, password: str, name: str) -> User:
    email = email.strip().lower()
    with store.lock:
        if any(u.email == email for u in store.users.values()):
            raise DomainError(409, "An account with this email already exists")
        user = User(
            id=store.next_id("user"),
            email=email,
            name=name.strip(),
            password_hash=hash_password(password),
        )
        store.users[user.id] = user
        return user


def login(store: Store, email: str, password: str) -> str:
    email = email.strip().lower()
    user = next((u for u in store.users.values() if u.email == email), None)
    if user is None:
        raise DomainError(401, "No account found for this email")
    if not verify_password(password, user.password_hash):
        raise DomainError(401, "Incorrect password")
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "jti": secrets.token_urlsafe(12),
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    return jwt.encode(claims, _jwt_secret(), algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "jti", "exp"]},
        )
    except jwt.PyJWTError:
        return None


def logout(store: Store, token: str) -> None:
    claims = _decode_token(token)
    if claims is not None:
        store.revoked_jtis.add(claims["jti"])


def user_for_token(store: Store, token: str | None) -> User | None:
    if not token:
        return None
    claims = _decode_token(token)
    if claims is None or claims["jti"] in store.revoked_jtis:
        return None
    try:
        return store.users.get(int(claims["sub"]))
    except ValueError:
        return None


# --- Catalog --------------------------------------------------------------------


@dataclass
class SearchPage:
    items: list[Book]
    total: int
    page: int
    page_size: int


def search_books(
    store: Store, q: str | None = None, genre: str | None = None, page: int = 1, page_size: int = 10
) -> SearchPage:
    books = sorted(store.books.values(), key=lambda b: b.id)
    if q:
        needle = q.strip()
        books = [b for b in books if needle.lower() in b.title.lower() or needle in b.author]
    total = len(books)
    if genre:
        books = [b for b in books if genre.lower() in b.genres]
    start = (page - 1) * page_size
    return SearchPage(
        items=books[start : start + page_size], total=total, page=page, page_size=page_size
    )


def get_book(store: Store, book_id: int) -> Book:
    book = store.books.get(book_id)
    if book is None:
        raise DomainError(404, f"Book {book_id} not found")
    return book


# --- Cart -----------------------------------------------------------------------


@dataclass
class CartLineView:
    book: Book
    quantity: int
    line_total: Decimal


@dataclass
class CartView:
    lines: list[CartLineView]
    totals: pricing.Totals


def view_cart(store: Store, user: User) -> CartView:
    cart = store.cart_for(user.id)
    lines = [
        CartLineView(
            book=store.books[book_id],
            quantity=qty,
            line_total=pricing.money(store.books[book_id].price * qty),
        )
        for book_id, qty in cart.lines.items()
    ]
    coupon = store.coupons.get(cart.coupon_code) if cart.coupon_code else None
    totals = pricing.calculate_totals(
        [(line.book.price, line.quantity) for line in lines], coupon, today()
    )
    return CartView(lines=lines, totals=totals)


def add_to_cart(store: Store, user: User, book_id: int, quantity: int) -> CartView:
    book = get_book(store, book_id)
    with store.lock:
        cart = store.cart_for(user.id)
        new_quantity = cart.lines.get(book_id, 0) + quantity
        if new_quantity > pricing.MAX_QUANTITY_PER_LINE:
            raise DomainError(
                422, f"You can order at most {pricing.MAX_QUANTITY_PER_LINE} copies of a book"
            )
        if new_quantity > book.stock:
            raise DomainError(409, f"Only {book.stock} copies of '{book.title}' are in stock")
        cart.lines[book_id] = new_quantity
    return view_cart(store, user)


def update_cart_item(store: Store, user: User, book_id: int, quantity: int) -> CartView:
    with store.lock:
        cart = store.cart_for(user.id)
        if book_id not in cart.lines:
            raise DomainError(404, f"Book {book_id} is not in your cart")
        cart.lines[book_id] = quantity
    return view_cart(store, user)


def remove_cart_item(store: Store, user: User, book_id: int) -> CartView:
    with store.lock:
        cart = store.cart_for(user.id)
        if cart.lines.pop(book_id, None) is None:
            raise DomainError(404, f"Book {book_id} is not in your cart")
    return view_cart(store, user)


def apply_coupon(store: Store, user: User, code: str) -> CartView:
    coupon = store.coupons.get(code.strip().upper())
    if coupon is None:
        raise DomainError(404, f"Coupon '{code}' does not exist")
    current = view_cart(store, user)
    try:
        pricing.validate_coupon(coupon, current.totals.subtotal, today())
    except pricing.CouponError as exc:
        raise DomainError(422, str(exc)) from exc
    store.cart_for(user.id).coupon_code = coupon.code
    return view_cart(store, user)


def remove_coupon(store: Store, user: User) -> CartView:
    store.cart_for(user.id).coupon_code = None
    return view_cart(store, user)


# --- Orders ---------------------------------------------------------------------


def checkout(store: Store, user: User) -> Order:
    with store.lock:
        cart_view = view_cart(store, user)
        if not cart_view.lines:
            raise DomainError(400, "Your cart is empty")
        for line in cart_view.lines:
            if line.quantity > line.book.stock:
                raise DomainError(
                    409, f"Only {line.book.stock} copies of '{line.book.title}' are in stock"
                )
        for line in cart_view.lines:
            line.book.stock -= line.quantity
        totals = cart_view.totals
        order = Order(
            id=store.next_id("order"),
            user_id=user.id,
            lines=[
                OrderLine(
                    book_id=line.book.id,
                    title=line.book.title,
                    unit_price=line.book.price,
                    quantity=line.quantity,
                )
                for line in cart_view.lines
            ],
            subtotal=totals.subtotal,
            discount=totals.discount,
            shipping=totals.shipping,
            total=totals.total,
            coupon_code=totals.coupon_code,
            status="placed",
            created_at=datetime.now(UTC),
        )
        store.orders[order.id] = order
        store.carts[user.id] = Cart()
        return order


def list_orders(store: Store, user: User) -> list[Order]:
    return sorted(
        (o for o in store.orders.values() if o.user_id == user.id),
        key=lambda o: o.created_at,
        reverse=True,
    )


def get_order(store: Store, user: User, order_id: int) -> Order:
    order = store.orders.get(order_id)
    if order is None:
        raise DomainError(404, f"Order {order_id} not found")
    return order


def cancel_order(store: Store, user: User, order_id: int) -> Order:
    order = get_order(store, user, order_id)
    if order.user_id != user.id:
        raise DomainError(404, f"Order {order_id} not found")
    if order.status == "cancelled":
        raise DomainError(409, "This order is already cancelled")
    order.status = "cancelled"
    return order


def ship_order(store: Store, admin: User, order_id: int) -> Order:
    if not admin.is_admin:
        raise DomainError(403, "Only administrators can ship orders")
    order = store.orders.get(order_id)
    if order is None:
        raise DomainError(404, f"Order {order_id} not found")
    if order.status != "placed":
        raise DomainError(409, f"Cannot ship an order that is {order.status}")
    order.status = "shipped"
    return order


# --- Reviews --------------------------------------------------------------------


def list_reviews(store: Store, book_id: int) -> list[Review]:
    get_book(store, book_id)
    return [r for r in store.reviews.values() if r.book_id == book_id]


def add_review(store: Store, user: User, book_id: int, rating: int, comment: str) -> Review:
    get_book(store, book_id)
    with store.lock:
        if any(r.book_id == book_id and r.user_id == user.id for r in store.reviews.values()):
            raise DomainError(409, "You have already reviewed this book")
        review = Review(
            id=store.next_id("review"),
            book_id=book_id,
            user_id=user.id,
            rating=rating,
            comment=comment.strip(),
            created_at=datetime.now(UTC),
        )
        store.reviews[review.id] = review
        return review
