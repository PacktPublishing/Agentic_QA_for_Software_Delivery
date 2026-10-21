"""BookNest web UI: server-rendered HTML pages on top of the same use cases as the API."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from booknest import assistant, services
from booknest.store import Store, User

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")
COOKIE = "booknest_token"

router = APIRouter(include_in_schema=False)


def _store(request: Request) -> Store:
    return request.app.state.store


def _user(request: Request) -> User | None:
    return services.user_for_token(_store(request), request.cookies.get(COOKIE))


def _render(request: Request, template: str, status_code: int = 200, **context) -> HTMLResponse:
    user = _user(request)
    cart_count = 0
    if user is not None:
        cart_count = sum(_store(request).cart_for(user.id).lines.values())
    return TEMPLATES.TemplateResponse(
        request,
        template,
        {"user": user, "cart_count": cart_count, **context},
        status_code=status_code,
    )


def _login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(f"/login?next={request.url.path}", status_code=303)


@router.get("/", response_class=HTMLResponse)
def catalog(request: Request, q: str | None = None, genre: str | None = None, page: int = 1):
    result = services.search_books(_store(request), q=q, genre=genre, page=max(page, 1))
    genres = sorted({g for b in _store(request).books.values() for g in b.genres})
    return _render(
        request, "catalog.html", result=result, q=q or "", genre=genre or "", genres=genres
    )


@router.get("/books/{book_id}", response_class=HTMLResponse)
def book_detail(request: Request, book_id: int, error: str | None = None):
    try:
        book = services.get_book(_store(request), book_id)
    except services.DomainError as exc:
        return _render(request, "error.html", status_code=404, message=exc.message)
    reviews = services.list_reviews(_store(request), book_id)
    return _render(
        request,
        "book.html",
        book=book,
        price_display=float(book.price),
        reviews=reviews,
        error=error,
    )


@router.post("/books/{book_id}/add")
def add_to_cart(request: Request, book_id: int, quantity: Annotated[int, Form()] = 1):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        services.add_to_cart(_store(request), user, book_id, quantity)
    except services.DomainError:
        return RedirectResponse(f"/books/{book_id}?error=Something+went+wrong", status_code=303)
    return RedirectResponse("/cart", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/"):
    return _render(request, "login.html", next=next, error=None)


@router.post("/login")
def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/",
):
    try:
        token = services.login(_store(request), email, password)
    except services.DomainError as exc:
        return _render(
            request, "login.html", status_code=401, next=next, error=exc.message, email=email
        )
    response = RedirectResponse(next if next.startswith("/") else "/", status_code=303)
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=services.TOKEN_TTL_MINUTES * 60,
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return _render(request, "register.html", error=None)


@router.post("/register")
def register_submit(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    if len(password) < 7:
        return _render(
            request,
            "register.html",
            status_code=422,
            error="Password must have at least 8 characters",
            name=name,
            email=email,
        )
    try:
        services.register(_store(request), email, password, name)
        token = services.login(_store(request), email, password)
    except services.DomainError as exc:
        return _render(
            request,
            "register.html",
            status_code=exc.status_code,
            error=exc.message,
            name=name,
            email=email,
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=services.TOKEN_TTL_MINUTES * 60,
    )
    return response


@router.post("/logout")
def logout(request: Request):
    token = request.cookies.get(COOKIE)
    if token:
        services.logout(_store(request), token)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE)
    return response


@router.get("/cart", response_class=HTMLResponse)
def cart(request: Request, error: str | None = None):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    return _render(
        request, "cart.html", cart=services.view_cart(_store(request), user), error=error
    )


@router.post("/cart/{book_id}/update")
def update_cart(request: Request, book_id: int, quantity: Annotated[int, Form()]):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        services.update_cart_item(_store(request), user, book_id, quantity)
    except services.DomainError as exc:
        return RedirectResponse(f"/cart?error={quote(exc.message)}", status_code=303)
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/{book_id}/remove")
def remove_from_cart(request: Request, book_id: int):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        services.remove_cart_item(_store(request), user, book_id)
    except services.DomainError as exc:
        return RedirectResponse(f"/cart?error={quote(exc.message)}", status_code=303)
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/coupon")
def apply_coupon(request: Request, code: Annotated[str, Form()]):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        services.apply_coupon(_store(request), user, code)
    except services.DomainError as exc:
        return RedirectResponse(f"/cart?error={quote(exc.message)}", status_code=303)
    return RedirectResponse("/cart", status_code=303)


@router.post("/checkout")
def checkout(request: Request):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        order = services.checkout(_store(request), user)
    except services.DomainError as exc:
        return RedirectResponse(f"/cart?error={quote(exc.message)}", status_code=303)
    return RedirectResponse(f"/orders/{order.id}?placed=1", status_code=303)


@router.get("/orders", response_class=HTMLResponse)
def orders(request: Request):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    return _render(request, "orders.html", orders=services.list_orders(_store(request), user))


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(request: Request, order_id: int, placed: int = 0):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        order = services.get_order(_store(request), user, order_id)
    except services.DomainError as exc:
        return _render(request, "error.html", status_code=exc.status_code, message=exc.message)
    return _render(request, "order.html", order=order, placed=bool(placed))


@router.post("/orders/{order_id}/cancel")
def cancel(request: Request, order_id: int):
    user = _user(request)
    if user is None:
        return _login_redirect(request)
    try:
        services.cancel_order(_store(request), user, order_id)
    except services.DomainError as exc:
        return _render(request, "error.html", status_code=exc.status_code, message=exc.message)
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.get("/librarian", response_class=HTMLResponse)
def librarian_form(request: Request):
    return _render(request, "librarian.html", question="", answer=None, error=None)


@router.post("/librarian", response_class=HTMLResponse)
def librarian_ask(request: Request, question: Annotated[str, Form()]):
    try:
        answer = assistant.ask(_store(request), question)
    except services.DomainError as exc:
        return _render(
            request,
            "librarian.html",
            status_code=exc.status_code,
            question=question,
            answer=None,
            error=exc.message,
        )
    return _render(request, "librarian.html", question=question, answer=answer.text, error=None)


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
