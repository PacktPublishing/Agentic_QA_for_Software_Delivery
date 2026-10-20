# US-10 Review a book

**As a** customer
**I want to** rate and review books
**So that** other readers can benefit from my opinion

API: `GET /api/books/{id}/reviews`, `POST /api/books/{id}/reviews {"rating": 1-5, "comment": "..."}`

## Acceptance criteria

1. Anyone can read reviews; only logged-in customers can write them.
2. The rating is a whole number from 1 to 5 stars. Any other value is rejected with HTTP 422.
3. The comment is optional and has at most 500 characters.
4. A customer can review each book only once (HTTP 409 on the second attempt).
5. Reviewing a book that does not exist returns HTTP 404.
