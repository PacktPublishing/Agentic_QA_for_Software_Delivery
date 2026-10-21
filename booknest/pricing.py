"""Pricing rules for BookNest: subtotals, coupons, shipping and totals.

These functions are pure (no I/O, no store access) so they are easy to unit test.
The business rules they implement are documented in product/stories/.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from booknest.store import Coupon

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
SHIPPING_FEE = Decimal("4.99")
FREE_SHIPPING_THRESHOLD = Decimal("50.00")
MAX_QUANTITY_PER_LINE = 10


class CouponError(ValueError):
    """Raised when a coupon cannot be applied to an order."""


def money(value: Decimal) -> Decimal:
    """Round a monetary value to cents, half up."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal
    coupon_code: str | None = None
    coupon_error: str | None = None


def subtotal_of(lines: list[tuple[Decimal, int]]) -> Decimal:
    """Sum of unit price x quantity for every line."""
    return money(sum((price * quantity for price, quantity in lines), ZERO))


def validate_coupon(coupon: Coupon, subtotal: Decimal, today: date) -> None:
    if coupon.expires_on is not None and today > coupon.expires_on:
        raise CouponError(f"Coupon {coupon.code} expired on {coupon.expires_on.isoformat()}")
    if subtotal <= coupon.min_subtotal:
        raise CouponError(
            f"Coupon {coupon.code} requires a subtotal of at least ${coupon.min_subtotal}"
        )


def discount_for(coupon: Coupon, subtotal: Decimal) -> Decimal:
    if coupon.kind == "percent":
        return money(subtotal * coupon.value / Decimal(100))
    return ZERO


def shipping_for(subtotal: Decimal, discount: Decimal, free_shipping_coupon: bool) -> Decimal:
    if subtotal == ZERO or free_shipping_coupon:
        return ZERO
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return ZERO
    return SHIPPING_FEE


def calculate_totals(
    lines: list[tuple[Decimal, int]],
    coupon: Coupon | None,
    today: date,
) -> Totals:
    """Calculate the totals for a cart or an order.

    If the coupon is not valid for this cart, it is not applied and the reason is
    reported in ``coupon_error`` instead of raising.
    """
    subtotal = subtotal_of(lines)
    discount = ZERO
    free_shipping = False
    coupon_error = None

    if coupon is not None:
        try:
            validate_coupon(coupon, subtotal, today)
            discount = discount_for(coupon, subtotal)
            free_shipping = coupon.kind == "free_shipping"
        except CouponError as exc:
            coupon_error = str(exc)

    shipping = shipping_for(subtotal, discount, free_shipping)
    total = money(subtotal - discount + shipping)
    return Totals(
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        total=total,
        coupon_code=coupon.code if coupon is not None and coupon_error is None else None,
        coupon_error=coupon_error,
    )
