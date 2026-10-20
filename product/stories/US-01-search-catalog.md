# US-01 Search the catalog

**As a** visitor
**I want to** search the catalog by title or author and filter by genre
**So that** I can quickly find books I am interested in

API: `GET /api/books?q=&genre=&page=&page_size=`

## Acceptance criteria

1. Searching matches words in the book **title or author name**, ignoring upper/lower case.
   For example, `q=okafor` and `q=OKAFOR` both return the books by Marina Okafor.
2. The genre filter only returns books that include that genre.
3. The response includes `total`: the number of books that match **all** the filters
   (search text and genre), not just the ones on the current page.
4. Results are paginated: `page` starts at 1, `page_size` defaults to 10 and cannot exceed 50.
   An invalid `page` or `page_size` is rejected with HTTP 422.
5. A search with no matches returns an empty `items` list and `total` 0 (not an error).
6. Each book shows `in_stock: false` when it has no copies left.
