# US-03 Free shipping

**As a** customer
**I want to** know exactly how much I will pay for shipping
**So that** there are no surprises at checkout

API: `GET /api/cart` shows `shipping` and `total` for the current cart.

## Acceptance criteria

1. Standard shipping costs $4.99 per order.
2. Orders whose subtotal **after discounts** is $50.00 or more ship for free.
   For example, a $52.00 cart with WELCOME10 (subtotal after discount $46.80) pays $4.99 shipping.
3. The FREESHIP coupon makes shipping free regardless of the order value.
4. An empty cart has no shipping cost.
5. The total is: subtotal − discount + shipping.

The WELCOME10 and FREESHIP coupons are described in US-04.
