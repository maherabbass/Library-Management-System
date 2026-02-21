# Manual Testing Guide — Library Management System

Complete step-by-step walkthrough that exercises every endpoint and feature.

---

## URLs

| Service | URL |
|---------|-----|
| **Frontend (Netlify)** | https://library-man-sys.netlify.app |
| **Backend API (Cloud Run)** | https://library-app-qtegugoc4a-ew.a.run.app |
| **Swagger UI (interactive API docs)** | https://library-app-qtegugoc4a-ew.a.run.app/docs |

---

## Prerequisites

- A Google **or** GitHub account for OAuth login
- A second Google or GitHub account (to test multi-role scenarios)
- A browser with DevTools open (F12 → Network tab) to inspect requests
- `curl` or the Swagger UI for direct API testing

---

## How to authenticate in Swagger UI

After logging in through the frontend, copy your JWT and paste it into Swagger:

1. Log in at **https://library-man-sys.netlify.app**
2. Open DevTools → Application → Local Storage → `access_token` → copy the value
3. Open **https://library-app-qtegugoc4a-ew.a.run.app/docs**
4. Click **Authorize** (top right) → paste the token → **Authorize**

You can now click "Try it out" on any endpoint in Swagger.

---

## One-time Bootstrap: Getting Admin Access

New OAuth users are created as **MEMBER**. To test admin and librarian features you need at least one ADMIN account. Do this once:

1. Log in via the frontend — note the account email.
2. Open [Cloud SQL Studio](https://console.cloud.google.com/sql) → your instance → **Cloud SQL Studio**
3. Run this SQL (replace the email with yours):

```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'your-email@example.com';
```

4. Log out and log back in — the UI will now show the **Admin** link in the nav bar.

> From this point on you can promote/demote any other user through the UI or the `/api/v1/admin/users/{id}/role` endpoint.

---

## Test 1 — Health Check

**What it covers:** `GET /health`

### Via browser
Open: https://library-app-qtegugoc4a-ew.a.run.app/health

**Expected response:**
```json
{ "status": "ok", "version": "0.1.0" }
```

### Via curl
```bash
curl https://library-app-qtegugoc4a-ew.a.run.app/health
```

✅ Pass if status 200 and body matches above.

---

## Test 2 — Book Browsing (API public; frontend requires login)

**What it covers:** `GET /api/v1/books` with all filter combinations

> The API endpoints are public and work without a token. The frontend redirects to `/login` if you are not authenticated.

### 2-A List all books

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books"
```

**Expected:** 200, `total: 15`, array of 15 seeded books.

---

### 2-B Free-text search (`q`)

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books?q=dystopia"
```

**Expected:** Returns *1984*, *Brave New World*, *Fahrenheit 451*.

In the UI: type `dystopia` in the Search field → click Search.

---

### 2-C Author filter

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books?author=orwell"
```

**Expected:** Returns *1984* only.

---

### 2-D Tag filter

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books?tag=sci-fi"
```

**Expected:** Returns *Dune* and *The Hitchhiker's Guide to the Galaxy*.

---

### 2-E Status filter

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books?status=AVAILABLE"
```

**Expected:** All books are AVAILABLE initially.

---

### 2-F Pagination

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books?page=1&page_size=5"
```

**Expected:** `items` has 5 books, `pages: 3`, `total: 15`.

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books?page=3&page_size=5"
```

**Expected:** `items` has 5 books, `page: 3`.

---

### 2-G Get a single book

Pick any `id` from the list above, then:
```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/<id>"
```

**Expected:** 200 with the full book object.

---

## Test 3 — Authentication (OAuth Login)

**What it covers:** `GET /api/v1/auth/login/{provider}`, `GET /api/v1/auth/callback/{provider}`, `GET /api/v1/auth/me`

### 3-A Login with Google

1. Go to https://library-man-sys.netlify.app/login
2. Click **Continue with Google**
3. Complete the Google consent screen
4. You are redirected back to `/books` — the navbar shows your name and role badge

**Behind the scenes:**
- Browser → `GET /api/v1/auth/login/google`
- Google OAuth consent
- Google → `GET /api/v1/auth/callback/google`
- Backend creates user in DB, issues JWT
- Redirects to `https://library-man-sys.netlify.app/auth/callback?token=<jwt>`
- Frontend stores token, fetches `/auth/me`

### 3-B Verify current user

```bash
curl -H "Authorization: Bearer <your-token>" \
  https://library-app-qtegugoc4a-ew.a.run.app/api/v1/auth/me
```

**Expected:**
```json
{
  "id": "...",
  "email": "you@gmail.com",
  "name": "Your Name",
  "role": "MEMBER",
  "oauth_provider": "google",
  "created_at": "..."
}
```

### 3-C Login with GitHub (second account)

1. Log out (click Logout in the navbar)
2. Click **Continue with GitHub**
3. Complete GitHub auth

**Expected:** Redirected back to `/books`, different name in navbar, role = MEMBER.

### 3-D Unsupported provider (error path)

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/auth/login/twitter"
```

**Expected:** 400 `{"detail": "Unsupported provider: twitter"}`

---

## Test 4 — Member Flows

> Log in as any OAuth user (MEMBER role).

**What it covers:** `POST /api/v1/loans/checkout`, `POST /api/v1/loans/return`, `GET /api/v1/loans`

### 4-A View book detail and checkout

1. Click any book with status **AVAILABLE**
2. On the detail page, click **Checkout**
3. The status badge changes to **BORROWED**, the button changes to **Return Book**

Via API:
```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/checkout \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"book_id": "<uuid-of-available-book>"}'
```

**Expected:** 201
```json
{
  "id": "...",
  "book_id": "...",
  "user_id": "...",
  "checked_out_at": "...",
  "returned_at": null,
  "status": "OUT"
}
```

---

### 4-B View my loans

In the UI: click **My Loans** in the nav.

Via API:
```bash
curl -H "Authorization: Bearer <token>" \
  https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans
```

**Expected:** 200, `items` contains the loan just created.

---

### 4-C Return the book

In the UI: click **Return** on the loan row, or click **Return Book** on the book detail page.

Via API (use the `loan.id` from step 4-A):
```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/return \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"loan_id": "<loan-id>"}'
```

**Expected:** 200, `status: "RETURNED"`, `returned_at` is populated.

---

## Test 5 — Business Rule Enforcement

**What it covers:** Loan constraints at the DB level.

### 5-A Cannot checkout an already-borrowed book

1. Checkout a book (step 4-A)
2. Log in as a **different** user (second OAuth account)
3. Try to checkout the same book

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/checkout \
  -H "Authorization: Bearer <second-users-token>" \
  -H "Content-Type: application/json" \
  -d '{"book_id": "<same-borrowed-book-id>"}'
```

**Expected:** 409 `{"detail": "Book is already borrowed"}`

---

### 5-B Cannot return a loan that isn't yours

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/return \
  -H "Authorization: Bearer <second-users-token>" \
  -H "Content-Type: application/json" \
  -d '{"loan_id": "<first-users-loan-id>"}'
```

**Expected:** 403 `{"detail": "..."}`

---

### 5-C Cannot return an already-returned loan

Return a loan, then try to return it again:
```bash
# second return attempt
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/return \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"loan_id": "<already-returned-loan-id>"}'
```

**Expected:** 404

---

## Test 6 — RBAC Boundary Tests

**What it covers:** Permission enforcement on protected endpoints.

### 6-A Unauthenticated user cannot checkout

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/checkout \
  -H "Content-Type: application/json" \
  -d '{"book_id": "<any-id>"}'
```

**Expected:** 401 `{"detail": "Not authenticated"}`

---

### 6-B Member cannot create a book

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books \
  -H "Authorization: Bearer <member-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Hacked Book", "author": "Hacker"}'
```

**Expected:** 403 `{"detail": "Insufficient permissions"}`

---

### 6-C Member cannot delete a book

```bash
curl -X DELETE "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/<any-id>" \
  -H "Authorization: Bearer <member-token>"
```

**Expected:** 403

---

### 6-D Member cannot access admin endpoints

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/admin/users" \
  -H "Authorization: Bearer <member-token>"
```

**Expected:** 403

---

### 6-E Librarian cannot access admin endpoints

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/admin/users" \
  -H "Authorization: Bearer <librarian-token>"
```

**Expected:** 403

---

## Test 7 — Librarian Flows (Book Management)

> Requires LIBRARIAN or ADMIN role. Use Admin panel to promote a user first (see Bootstrap above).

**What it covers:** `POST /api/v1/books`, `PUT /api/v1/books/{id}`, `DELETE /api/v1/books/{id}`

### 7-A Create a book

In the UI: click **+ Add Book** in the navbar → fill the form → **Create Book**.

Via API:
```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books \
  -H "Authorization: Bearer <librarian-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Pragmatic Test",
    "author": "Test Author",
    "isbn": "9781234567890",
    "published_year": 2024,
    "description": "A book created during manual testing.",
    "tags": ["test", "manual"]
  }'
```

**Expected:** 201 with a new book object, `status: "AVAILABLE"`.

---

### 7-B Update a book

```bash
curl -X PUT "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/<new-book-id>" \
  -H "Authorization: Bearer <librarian-token>" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description during testing.", "tags": ["test", "updated"]}'
```

**Expected:** 200 with `description` and `tags` updated, `updated_at` refreshed.

---

### 7-C Delete a book

```bash
curl -X DELETE "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/<new-book-id>" \
  -H "Authorization: Bearer <librarian-token>"
```

**Expected:** 204 No Content. Confirm by trying `GET /api/v1/books/<id>` → 404.

---

### 7-D Cannot delete a book that is currently borrowed

1. Checkout a book as a member (step 4-A)
2. Try to delete it as librarian:

```bash
curl -X DELETE "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/<borrowed-book-id>" \
  -H "Authorization: Bearer <librarian-token>"
```

**Expected:** 409 `{"detail": "Cannot delete a book that is currently borrowed"}`

---

## Test 8 — AI Feature A: Metadata Enrichment

**What it covers:** `POST /api/v1/books/enrich` — requires LIBRARIAN or ADMIN

> This endpoint previews AI-generated metadata **without saving to DB**. The librarian reviews and decides what to save.

### 8-A Via UI

1. Log in as Librarian/Admin → click **+ Add Book**
2. Fill in **Title** and **Author** only
3. Click **✨ AI Enrich**
4. The AI panel appears with a generated summary, tags, and keywords
5. Click **Apply to form** → the description and tags fields are populated
6. Click **Create Book** to save

---

### 8-B Via API

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/enrich \
  -H "Authorization: Bearer <librarian-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Silmarillion",
    "author": "J.R.R. Tolkien",
    "description": "The history of the First Age of Middle-earth."
  }'
```

**Expected:** 200
```json
{
  "summary": "...",
  "tags": ["fantasy", "mythology", ...],
  "keywords": ["tolkien", "middle-earth", ...],
  "source": "openai"   // or "fallback" if AI not configured
}
```

---

### 8-C Member cannot call enrich

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/enrich \
  -H "Authorization: Bearer <member-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "author": "Me"}'
```

**Expected:** 403

---

## Test 9 — AI Feature B: Semantic Search

**What it covers:** `GET /api/v1/books/ai-search` — public endpoint

### 9-A Via UI

1. Click **AI Search** in the navbar (no login needed)
2. Type a natural language query: `"a book about a society under government control"`
3. Click **Search**
4. Results show ranked books with a badge: **✨ OpenAI** or **Keyword fallback**

---

### 9-B Via API

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/ai-search?q=survival+on+a+desert+planet&top_k=5"
```

**Expected:** 200
```json
{
  "items": [...],     // ranked by semantic similarity
  "total": 5,
  "source": "openai", // or "fallback"
  "query": "survival on a desert planet"
}
```

Top result should be *Dune* by Frank Herbert.

---

### 9-C Different queries to test ranking

| Query | Expected top result |
|-------|---------------------|
| `"totalitarian surveillance state"` | *1984* |
| `"guide to software craftsmanship"` | *Clean Code* or *The Pragmatic Programmer* |
| `"history of human civilisation"` | *Sapiens* |
| `"comedy science fiction space travel"` | *The Hitchhiker's Guide to the Galaxy* |

---

## Test 10 — AI Feature C: Ask the Library

**What it covers:** `POST /api/v1/books/ask` — requires any authenticated user

### 10-A Via UI

1. Log in → click **Ask Library** in the navbar
2. Ask: `"Do you have any books about dystopian societies?"`
3. The assistant responds with an answer that **only references real books** from the database
4. Source books are listed below the answer as clickable links

---

### 10-B Via API

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What programming books do you have?"}'
```

**Expected:** 200
```json
{
  "answer": "We have the following programming books: ...",
  "books": [
    { "title": "Clean Code", "author": "Robert C. Martin", ... },
    { "title": "The Pragmatic Programmer", ... },
    { "title": "Design Patterns", ... }
  ],
  "source": "openai"
}
```

---

### 10-C Grounding — no hallucinated books

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Do you have Harry Potter?"}'
```

**Expected:** The answer says the book is **not in the library** — it does not invent it.
`"books": []` or only real books are cited.

---

### 10-D Unauthenticated user cannot use chat

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Any sci-fi?"}'
```

**Expected:** 401

---

## Test 11 — Admin Flows

**What it covers:** `GET /api/v1/admin/users`, `PATCH /api/v1/admin/users/{id}/role`

> Requires ADMIN role.

### 11-A List all users

In the UI: click **Admin** in the navbar.

Via API:
```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/admin/users" \
  -H "Authorization: Bearer <admin-token>"
```

**Expected:** 200, array of all registered users with their roles.

---

### 11-B Promote a user to Librarian

In the UI: find the user in the table → change the role dropdown to **LIBRARIAN**.

Via API (use the user `id` from step 11-A):
```bash
curl -X PATCH "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/admin/users/<user-id>/role" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "LIBRARIAN"}'
```

**Expected:** 200 with the user object showing `"role": "LIBRARIAN"`.

Verify: ask that user to create a book (step 7-A) — it should now succeed.

---

### 11-C Promote a user to Admin

```bash
curl -X PATCH "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/admin/users/<user-id>/role" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "ADMIN"}'
```

**Expected:** 200 with `"role": "ADMIN"`.

---

### 11-D Demote back to Member

```bash
curl -X PATCH "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/admin/users/<user-id>/role" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "MEMBER"}'
```

**Expected:** 200. Confirm they can no longer create books (step 6-B).

---

### 11-E Librarian/Admin can see all loans

When logged in as Librarian or Admin, **My Loans** shows loans from ALL users.

```bash
curl "https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans" \
  -H "Authorization: Bearer <admin-token>"
```

**Expected:** Loans from every user, includes `user_id` column.

Member token on the same endpoint returns only their own loans.

---

## Test 12 — Invalid Input Validation

### 12-A Create book with missing required fields

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books \
  -H "Authorization: Bearer <librarian-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "No Author Book"}'
```

**Expected:** 422 Unprocessable Entity with validation details.

---

### 12-B Checkout a non-existent book

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/loans/checkout \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"book_id": "00000000-0000-0000-0000-000000000000"}'
```

**Expected:** 404

---

### 12-C Ask with empty question

```bash
curl -X POST https://library-app-qtegugoc4a-ew.a.run.app/api/v1/books/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": ""}'
```

**Expected:** 422

---

## Full Test Checklist

Use this to track your progress:

```
HEALTH
[ ] GET /health → 200

BOOKS (API public; frontend requires login)
[ ] GET /api/v1/books → 200, 15 books
[ ] GET /api/v1/books?q=dystopia → filtered results
[ ] GET /api/v1/books?author=orwell → 1984 only
[ ] GET /api/v1/books?tag=sci-fi → 2 results
[ ] GET /api/v1/books?status=AVAILABLE → all available
[ ] GET /api/v1/books?page=1&page_size=5 → 5 items, pages=3
[ ] GET /api/v1/books/<id> → single book

AUTH
[ ] GET /api/v1/auth/login/google → redirects to Google
[ ] GET /api/v1/auth/callback/google → JWT issued, redirect to frontend
[ ] GET /api/v1/auth/login/github → redirects to GitHub
[ ] GET /api/v1/auth/me → returns current user
[ ] GET /api/v1/auth/login/twitter → 400 unsupported

LOANS (member)
[ ] POST /api/v1/loans/checkout → 201, OUT
[ ] GET /api/v1/loans → member sees own loans only
[ ] POST /api/v1/loans/checkout same book → 409
[ ] POST /api/v1/loans/return → 200, RETURNED
[ ] POST /api/v1/loans/return same loan again → 404

RBAC BOUNDARIES
[ ] POST /api/v1/loans/checkout (no auth) → 401
[ ] POST /api/v1/books (member) → 403
[ ] DELETE /api/v1/books/<id> (member) → 403
[ ] GET /api/v1/admin/users (member) → 403
[ ] GET /api/v1/admin/users (librarian) → 403
[ ] POST /api/v1/books/enrich (member) → 403

BOOKS (librarian/admin)
[ ] POST /api/v1/books → 201
[ ] PUT /api/v1/books/<id> → 200, updated
[ ] DELETE /api/v1/books/<id> → 204
[ ] DELETE borrowed book → 409
[ ] GET /api/v1/loans (admin) → all users' loans

AI — ENRICH
[ ] POST /api/v1/books/enrich → summary + tags + keywords
[ ] source field is "openai" or "fallback"

AI — SEMANTIC SEARCH
[ ] GET /api/v1/books/ai-search?q=... → ranked results
[ ] source field is "openai" or "fallback"
[ ] Correct book rises to top for descriptive query

AI — CHAT
[ ] POST /api/v1/books/ask → grounded answer + cited books
[ ] Unknown book → not hallucinated
[ ] POST /api/v1/books/ask (no auth) → 401

ADMIN
[ ] GET /api/v1/admin/users → all users
[ ] PATCH /api/v1/admin/users/<id>/role → role updated
[ ] Promoted user can now perform actions for new role
[ ] Demoted user loses access

VALIDATION
[ ] POST /api/v1/books missing author → 422
[ ] POST /api/v1/loans/checkout fake uuid → 404
[ ] POST /api/v1/books/ask empty question → 422
```

---

## Endpoints Summary

| Method | Path | Auth | Role |
|--------|------|------|------|
| GET | `/health` | No | — |
| GET | `/api/v1/auth/login/{provider}` | No | — |
| GET | `/api/v1/auth/callback/{provider}` | No | — |
| GET | `/api/v1/auth/me` | Yes | Any |
| GET | `/api/v1/books` | No | — |
| GET | `/api/v1/books/{id}` | No | — |
| GET | `/api/v1/books/ai-search` | No | — |
| POST | `/api/v1/books` | Yes | Librarian, Admin |
| PUT | `/api/v1/books/{id}` | Yes | Librarian, Admin |
| DELETE | `/api/v1/books/{id}` | Yes | Librarian, Admin |
| POST | `/api/v1/books/enrich` | Yes | Librarian, Admin |
| POST | `/api/v1/books/ask` | Yes | Any |
| POST | `/api/v1/loans/checkout` | Yes | Any |
| POST | `/api/v1/loans/return` | Yes | Any |
| GET | `/api/v1/loans` | Yes | Any (member: own only) |
| GET | `/api/v1/admin/users` | Yes | Admin |
| PATCH | `/api/v1/admin/users/{id}/role` | Yes | Admin |
