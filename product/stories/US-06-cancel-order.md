# US-06 Cancel an order

**As a** customer
**I want to** cancel an order I no longer want
**So that** I am not charged for it

API: `POST /api/orders/{id}/cancel`

## Acceptance criteria

1. Only orders in status `placed` can be cancelled. Orders that are `shipped`, `delivered` or
   already `cancelled` cannot (HTTP 409).
2. A customer can only cancel their own orders (HTTP 404 for others).
3. Cancelling an order returns the ordered copies to stock.
4. A cancelled order keeps its lines and totals for the customer's records.

Administrators move orders to `shipped` with `POST /api/orders/{id}/ship`.
