# US-09 Ask the Librarian

**As a** visitor
**I want to** describe what I like and get book recommendations
**So that** I discover books I would enjoy

API: `POST /api/assistant/ask {"question": "..."}` · UI: `/librarian`

## Acceptance criteria

1. Recommendations only include books that exist in the BookNest catalog.
2. The librarian does not recommend books that are out of stock, or clearly says they are out of stock.
3. Prices mentioned in an answer match the catalog.
4. The librarian never invents discounts, coupons or policies; it only mentions the coupons listed in US-04.
5. Questions unrelated to books are politely redirected to books.
6. Answers are shorter than 150 words.
