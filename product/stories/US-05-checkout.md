# US-05 Check out

**As a** customer
**I want to** turn my cart into an order
**So that** the books are shipped to me

API: `POST /api/orders`

## Acceptance criteria

1. Checking out an empty cart is rejected with HTTP 400.
2. Checkout fails with HTTP 409 if any line asks for more copies than are in stock.
3. A successful checkout returns HTTP 201 with the order in status `placed`, and its subtotal,
   discount, shipping and total match what the cart showed.
4. The stock of each ordered book is reduced by the ordered quantity.
5. After checkout the cart is empty and the coupon is removed.
6. A customer can list their own orders (`GET /api/orders`) and open one (`GET /api/orders/{id}`).
   A customer can never see another customer's orders (HTTP 404).
