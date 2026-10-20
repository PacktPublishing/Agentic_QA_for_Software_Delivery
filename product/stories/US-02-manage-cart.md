# US-02 Manage my shopping cart

**As a** logged-in customer
**I want to** add books to my cart and change quantities
**So that** I can prepare an order

API: `GET /api/cart`, `POST /api/cart/items`, `PATCH /api/cart/items/{book_id}`, `DELETE /api/cart/items/{book_id}`
(all require `Authorization: Bearer <token>`)

## Acceptance criteria

1. A customer must be logged in to see or change a cart (HTTP 401 otherwise).
2. A customer can add between 1 and 10 copies of a book per cart line.
   Adding more copies of a book already in the cart increases its quantity.
3. A cart line can never hold more copies than the book has in stock, whether the quantity
   was set when adding or when updating the line (HTTP 409).
4. Updating a line accepts quantities from 1 to 10 only; any other value is rejected with
   HTTP 422. Removing a book is done with DELETE.
5. Out-of-stock books cannot be added to the cart (HTTP 409).
6. The cart shows each line's unit price, quantity and line total, plus the cart totals.
