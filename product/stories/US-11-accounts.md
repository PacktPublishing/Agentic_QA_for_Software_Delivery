# US-11 Create an account and log in

**As a** visitor
**I want to** create an account and log in
**So that** I can buy books

API: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

## Acceptance criteria

1. Registration requires a valid email, a name, and a password of **at least 8 characters**.
   Invalid data is rejected with HTTP 422.
2. Emails are unique and case-insensitive (HTTP 409 for a duplicate).
3. Logging in with valid credentials returns a bearer token.
4. A failed login returns HTTP 401 with the **same generic message** whether the email is
   unknown or the password is wrong, so attackers cannot discover which emails have accounts.
5. `GET /api/auth/me` returns the logged-in customer and never exposes the password.

Test accounts: `alice@example.com` / `alice-password-1`, `bruno@example.com` / `bruno-password-1`,
admin `admin@booknest.test` / `admin-password-1`.
