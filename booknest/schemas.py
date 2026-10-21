"""Request and response models for the BookNest REST API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from booknest import services
from booknest.store import Book, Order, Review, User


class RegisterRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=7, max_length=128)
    name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str

    @classmethod
    def of(cls, user: User) -> UserOut:
        return cls(id=user.id, email=user.email, name=user.name)


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    price: Decimal
    stock: int
    in_stock: bool
    genres: list[str]
    description: str
    published_year: int

    @classmethod
    def of(cls, book: Book) -> BookOut:
        return cls(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            price=book.price,
            stock=book.stock,
            in_stock=book.stock > 0,
            genres=book.genres,
            description=book.description,
            published_year=book.published_year,
        )


class BookPage(BaseModel):
    items: list[BookOut]
    total: int
    page: int
    page_size: int


class AddCartItemRequest(BaseModel):
    book_id: int
    quantity: int = Field(default=1, ge=1, le=10)


class UpdateCartItemRequest(BaseModel):
    quantity: int


class ApplyCouponRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class CartLineOut(BaseModel):
    book_id: int
    title: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class CartOut(BaseModel):
    lines: list[CartLineOut]
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal
    coupon_code: str | None
    coupon_error: str | None

    @classmethod
    def of(cls, cart: services.CartView) -> CartOut:
        t = cart.totals
        return cls(
            lines=[
                CartLineOut(
                    book_id=line.book.id,
                    title=line.book.title,
                    unit_price=line.book.price,
                    quantity=line.quantity,
                    line_total=line.line_total,
                )
                for line in cart.lines
            ],
            subtotal=t.subtotal,
            discount=t.discount,
            shipping=t.shipping,
            total=t.total,
            coupon_code=t.coupon_code,
            coupon_error=t.coupon_error,
        )


class OrderLineOut(BaseModel):
    book_id: int
    title: str
    unit_price: Decimal
    quantity: int


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    lines: list[OrderLineOut]
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal
    coupon_code: str | None
    created_at: datetime

    @classmethod
    def of(cls, order: Order) -> OrderOut:
        return cls(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            lines=[
                OrderLineOut(
                    book_id=line.book_id,
                    title=line.title,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                )
                for line in order.lines
            ],
            subtotal=order.subtotal,
            discount=order.discount,
            shipping=order.shipping,
            total=order.total,
            coupon_code=order.coupon_code,
            created_at=order.created_at,
        )


class ReviewRequest(BaseModel):
    rating: int = Field(ge=0, le=5)
    comment: str = Field(default="", max_length=500)


class ReviewOut(BaseModel):
    id: int
    book_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime

    @classmethod
    def of(cls, review: Review) -> ReviewOut:
        return cls(
            id=review.id,
            book_id=review.book_id,
            user_id=review.user_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
        )


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AskResponse(BaseModel):
    answer: str
    books_considered: list[int]
