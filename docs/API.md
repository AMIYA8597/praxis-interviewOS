# API Guidelines

## Pagination
All list endpoints use cursor-based pagination. This prevents skipped or duplicated rows under concurrent inserts, unlike naive OFFSET/LIMIT.

We use a composite cursor: created_at and id (e.g., cursor=1690000000.123456_UUID).
The query logic is:
`sql
WHERE (created_at, id) < (:cursor_created_at, :cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT :limit
`
The client receives 
ext_cursor in the response, which is 
ull if there are no more items.
