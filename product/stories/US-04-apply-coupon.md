# US-04 Apply a coupon

**As a** customer
**I want to** apply a coupon code to my cart
**So that** I get the discount I was promised

API: `POST /api/cart/coupon {"code": "..."}`, `DELETE /api/cart/coupon`

## Coupons currently available

| Code       | Benefit                 | Minimum subtotal | Expires     |
|------------|-------------------------|------------------|-------------|
| WELCOME10  | 10% off the subtotal    | $20.00           | never       |
| BOOKWORM25 | 25% off the subtotal    | $100.00          | never       |
| FREESHIP   | free shipping           | none             | never       |
| SUMMER2024 | 15% off the subtotal    | none             | 2024-08-31  |

## Acceptance criteria

1. Coupon codes are case-insensitive (`welcome10` works like `WELCOME10`).
2. A coupon can be applied when the cart subtotal is **equal to or greater than** its minimum subtotal.
   For example, WELCOME10 works on a cart with a subtotal of exactly $20.00.
3. Applying a coupon below its minimum subtotal is rejected with HTTP 422 and a message that
   states the minimum.
4. Expired coupons are rejected with HTTP 422. Unknown codes are rejected with HTTP 404.
5. Only one coupon applies per cart; applying a new coupon replaces the previous one.
6. Percentage discounts are calculated on the subtotal and rounded to the nearest cent.
7. If the cart changes and no longer meets the coupon minimum, the discount is removed and the
   cart explains why in `coupon_error`.
