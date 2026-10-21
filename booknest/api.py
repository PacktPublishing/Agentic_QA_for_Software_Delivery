"""BookNest REST API (mounted under /api)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from booknest import assistant, services
from booknest.schemas import (
    AddCartItemRequest,
    ApplyCouponRequest,
    AskRequest,
    AskResponse,
    BookOut,
    BookPage,
    CartOut,
    LoginRequest,
    OrderOut,
    RegisterRequest,
    ReviewOut,
    ReviewRequest,
    TokenResponse,
    UpdateCartItemRequest,
    UserOut,
)
from booknest.store import Store, User

router = APIRouter(prefix="/api")


def get_store(request: Request) -> Store:
    return request.app.state.store


StoreDep = Annotated[Store, Depends(get_store)]


def current_user(store: StoreDep, authorization: Annotated[str | None, Header()] = None) -> User:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = services.user_for_token(store, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


UserDep = Annotated[User, Depends(current_user)]


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Auth -----------------------------------------------------------------------


@router.post("/auth/register", status_code=201, response_model=UserOut, tags=["auth"])
def register(body: RegisterRequest, store: StoreDep) -> UserOut:
    return UserOut.of(services.register(store, body.email, body.password, body.name))


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest, store: StoreDep) -> TokenResponse:
    return TokenResponse(token=services.login(store, body.email, body.password))


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: UserDep) -> UserOut:
    return UserOut.of(user)


# --- Catalog --------------------------------------------------------------------


@router.get("/books", response_model=BookPage, tags=["catalog"])
def list_books(
    store: StoreDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    genre: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> BookPage:
    result = services.search_books(store, q=q, genre=genre, page=page, page_size=page_size)
    return BookPage(
        items=[BookOut.of(b) for b in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/books/{book_id}", response_model=BookOut, tags=["catalog"])
def get_book(book_id: int, store: StoreDep) -> BookOut:
    return BookOut.of(services.get_book(store, book_id))


@router.get("/books/{book_id}/reviews", response_model=list[ReviewOut], tags=["reviews"])
def list_reviews(book_id: int, store: StoreDep) -> list[ReviewOut]:
    return [ReviewOut.of(r) for r in services.list_reviews(store, book_id)]


@router.post(
    "/books/{book_id}/reviews", status_code=201, response_model=ReviewOut, tags=["reviews"]
)
def add_review(book_id: int, body: ReviewRequest, store: StoreDep, user: UserDep) -> ReviewOut:
    return ReviewOut.of(services.add_review(store, user, book_id, body.rating, body.comment))


# --- Cart -----------------------------------------------------------------------


@router.get("/cart", response_model=CartOut, tags=["cart"])
def get_cart(store: StoreDep, user: UserDep) -> CartOut:
    return CartOut.of(services.view_cart(store, user))


@router.post("/cart/items", response_model=CartOut, tags=["cart"])
def add_cart_item(body: AddCartItemRequest, store: StoreDep, user: UserDep) -> CartOut:
    return CartOut.of(services.add_to_cart(store, user, body.book_id, body.quantity))


@router.patch("/cart/items/{book_id}", response_model=CartOut, tags=["cart"])
def update_cart_item(
    book_id: int, body: UpdateCartItemRequest, store: StoreDep, user: UserDep
) -> CartOut:
    return CartOut.of(services.update_cart_item(store, user, book_id, body.quantity))


@router.delete("/cart/items/{book_id}", response_model=CartOut, tags=["cart"])
def remove_cart_item(book_id: int, store: StoreDep, user: UserDep) -> CartOut:
    return CartOut.of(services.remove_cart_item(store, user, book_id))


@router.post("/cart/coupon", response_model=CartOut, tags=["cart"])
def apply_coupon(body: ApplyCouponRequest, store: StoreDep, user: UserDep) -> CartOut:
    return CartOut.of(services.apply_coupon(store, user, body.code))


@router.delete("/cart/coupon", response_model=CartOut, tags=["cart"])
def remove_coupon(store: StoreDep, user: UserDep) -> CartOut:
    return CartOut.of(services.remove_coupon(store, user))


# --- Orders ---------------------------------------------------------------------


@router.post("/orders", status_code=201, response_model=OrderOut, tags=["orders"])
def checkout(store: StoreDep, user: UserDep) -> OrderOut:
    return OrderOut.of(services.checkout(store, user))


@router.get("/orders", response_model=list[OrderOut], tags=["orders"])
def list_orders(store: StoreDep, user: UserDep) -> list[OrderOut]:
    return [OrderOut.of(o) for o in services.list_orders(store, user)]


@router.get("/orders/{order_id}", response_model=OrderOut, tags=["orders"])
def get_order(order_id: int, store: StoreDep, user: UserDep) -> OrderOut:
    return OrderOut.of(services.get_order(store, user, order_id))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut, tags=["orders"])
def cancel_order(order_id: int, store: StoreDep, user: UserDep) -> OrderOut:
    return OrderOut.of(services.cancel_order(store, user, order_id))


@router.post("/orders/{order_id}/ship", response_model=OrderOut, tags=["admin"])
def ship_order(order_id: int, store: StoreDep, user: UserDep) -> OrderOut:
    return OrderOut.of(services.ship_order(store, user, order_id))


# --- Ask the Librarian (AI feature) ---------------------------------------------


@router.post("/assistant/ask", response_model=AskResponse, tags=["assistant"])
def ask_librarian(body: AskRequest, store: StoreDep) -> AskResponse:
    answer = assistant.ask(store, body.question)
    return AskResponse(answer=answer.text, books_considered=answer.book_ids)


# --- Test support ---------------------------------------------------------------


@router.post("/testing/reset", status_code=204, tags=["testing"])
def reset(request: Request, store: StoreDep) -> None:
    if not request.app.state.testing_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    store.reset()
