# CLAUDE.md — Mini Library Management System (FastAPI)

Claude: You are building this project from an empty folder. Follow an engineering workflow: explore → plan → implement → verify. Keep the repo runnable at all times and ship a deployed URL.

---

## 1 Project summary

Build a **Mini Library Management System** with:

### Minimum features
- **Book Management (CRUD):** Add, edit, delete books (title, author, and reasonable metadata).
- **Check-in / Check-out:** Borrow/return books with correct state transitions.
- **Search:** Find books by title, author, and other fields.
- **AI feature(s):** Implement at least one meaningful AI capability.

### Requirements
- Source code + **README** (how to run locally + how to deploy).
- **Deploy** the app and provide a **live URL**.
- **Authentication with SSO**, preferably with **roles/permissions**.
- Add extra features to demonstrate creativity.

---

## 2 Non-negotiable workflow (do this every time)

### 2.1 Explore → Plan → Code
1. **Plan Mode first:** Propose architecture + DB schema + API endpoints + auth approach + AI feature design + deployment plan.
2. **Implementation plan:** Break into phases with clear exit criteria and test/verification commands.
3. **Implement one phase at a time:** Small, reviewable commits/steps.

### 2.2 Verification is mandatory
For every phase:
- run lint/format
- run tests
- start the server and hit at least one real endpoint
- fix failures (no “should work”)

If a check cannot be run, explain why and provide a fallback validation step.

---

## 3 Tech stack (FastAPI backend)

### Backend (required)
- **FastAPI (Python)**
- **PostgreSQL**
- **Pydantic v2** schemas
- **Uvicorn** server
- **pytest** for tests
- **ruff** for lint, **black** for format
- **httpx** for API tests (FastAPI TestClient or AsyncClient)

### Frontend (keep simple)
A small separate frontend (React/Next/Vite) that calls the FastAPI API  
keep it minimal and prioritize backend completeness.

### Deployment (required)
- Backend deploy: **Render** / **Cloud Run** (pick one)
- DB: managed Postgres
- Document deployed URL + env vars in README

---

## 4 Authentication + SSO + RBAC (required)

### Must have
- **SSO OAuth** login (Google + GitHub preferred)
- Persist user in DB on first login
- **RBAC roles** enforced server-side

### Roles
- **Admin**: manage users/roles + full access
- **Librarian**: create/edit/delete books, manage loans
- **Member**: view/search books, borrow/return (only their own loans)

### Enforcement
- RBAC checks must be done in the API layer (dependencies / decorators).
- UI must not be the only enforcement.

---

## 5 Core domain & data model (baseline)

### Entities
**Book**
- id (uuid)
- title (required)
- author (required)
- isbn (optional, unique if present)
- published_year (optional)
- tags (optional array or separate table)
- description (optional)
- status: AVAILABLE | BORROWED
- created_at / updated_at

**User**
- id (uuid)
- email (unique)
- name
- role: ADMIN | LIBRARIAN | MEMBER
- oauth_provider (e.g., google/github)
- oauth_subject (provider user id)
- created_at

**Loan**
- id (uuid)
- book_id (FK)
- user_id (FK)
- checked_out_at
- returned_at (nullable)
- status: OUT | RETURNED

### Constraints
- A book can have **at most one active loan**.
- Borrowing an already-borrowed book must fail with a clear error.

---

## 6 API design (required)

Implement a versioned API:
- `/api/v1`

### Endpoints (minimum)
**Auth**
- `/api/v1/auth/login/{provider}` (OAuth start)
- `/api/v1/auth/callback/{provider}` (OAuth callback)
- `/api/v1/auth/me` (current user)

**Books**
- `GET /api/v1/books` (list + filters + pagination + text search)
- `POST /api/v1/books` (Librarian/Admin)
- `GET /api/v1/books/{id}`
- `PUT /api/v1/books/{id}` (Librarian/Admin)
- `DELETE /api/v1/books/{id}` (Librarian/Admin)

**Loans**
- `POST /api/v1/loans/checkout` (Member/Librarian/Admin; rules apply)
- `POST /api/v1/loans/return` (Member returns own; Librarian/Admin can return any)
- `GET /api/v1/loans` (Member: own only; Librarian/Admin: all)

**Users (Admin)**
- `GET /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{id}/role`

### Notes
- Use Pydantic schemas for request/response.
- Validate input with Pydantic and return consistent error responses.

---

## 7 Search (required)

Implement **two layers**:
1) **Basic search**: Postgres `ILIKE` or full-text search over title/author/isbn/tags
2) Optional enhancement: Postgres FTS (`tsvector`) for better ranking

Must support query params like:
- `q=...`
- `author=...`
- `tag=...`
- `status=AVAILABLE|BORROWED`
- pagination: `page`, `page_size`

---

## 8 AI features

Implement fully, with graceful fallback if AI keys are missing.

### A — Auto metadata enrichment
On book create/update:
- generate **summary**, **tags**, and **keywords** from title/author/description
- librarian can accept/edit output before saving
- store results in DB

### B — Semantic search (embeddings)
- compute embeddings for (title + author + description)
- store vectors (Postgres pgvector if available, or a simple vector store)
- add `/api/v1/books/ai-search?q=...` returning ranked matches
- fallback to basic search if embeddings unavailable

### C — “Ask the Library” assistant (grounded)
- chat endpoint that answers questions using ONLY database facts
- implement retrieval from DB and craft a constrained prompt
- prevent hallucinated books (always cite DB results internally)

### Safety rules
- Never expose secrets or environment variables.
- Treat DB as source of truth. No invented records.

---

## 9 Repository structure (target)

Use a clean structure like:

- `app/`
  - `main.py`
  - `core/` (config, security, logging)
  - `db/` (session, base, migrations)
  - `models/`
  - `schemas/`
  - `api/` (routers)
  - `services/` (business logic, AI)
  - `auth/` (OAuth, RBAC deps)
  - `tests/`
- `pyproject.toml`
- `.env.example`
- `README.md`
- `Dockerfile` + `docker-compose.yml`

---

## 10 Implementation phases & tasks (do in order)

### Phase 0 — Bootstrap & tooling
**Tasks**
- Initialize Python project (`pyproject.toml`) with dependencies:
  - fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings
  - python-jose (or authlib), authlib (OAuth), passlib/bcrypt if needed
  - ruff, black, pytest, httpx
- Add `.env.example`
- Add docker-compose with Postgres
- Create base FastAPI app with health endpoint: `GET /health`

**Exit criteria**
- `docker compose up` starts Postgres
- `uvicorn app.main:app --reload` runs
- `GET /health` returns 200

---

### Phase 1 — DB schema + migrations
**Tasks**
- Implement SQLAlchemy models (Book, User, Loan)
- Alembic migrations
- Seed script (10–20 books + 3 users with roles)

**Exit criteria**
- `alembic upgrade head` works
- seed script works
- tests can connect to DB

---

### Phase 2 — Books CRUD + basic search
**Tasks**
- Implement routers + services for Books
- Validation + pagination
- Basic text search & filters
- Add tests for CRUD + search

**Exit criteria**
- CRUD works with correct status codes
- search works and is covered by tests

---

### Phase 3 — SSO OAuth + RBAC
**Tasks**
- Implement OAuth for Google + GitHub (Authlib recommended)
- Create user on first login; store provider+subject
- Session/JWT strategy:
  - either secure cookie session or JWT access token
- Add RBAC dependencies (require_role / require_any_role)
- Admin endpoints to list users and change roles
- Add tests for permission enforcement

**Exit criteria**
- Login works locally (document setup)
- RBAC prevents unauthorized actions (tests)

---

### Phase 4 — Loans: check-out / return + rules
**Tasks**
- Checkout endpoint:
  - fails if book already borrowed
  - creates active loan and marks book BORROWED
- Return endpoint:
  - sets returned_at, marks book AVAILABLE
  - members can only return own loans
- Add tests for race/rule correctness (transactional update)

**Exit criteria**
- correct state transitions
- permission + business rules enforced and tested

---

### Phase 5 — AI feature(s)
**Tasks**
- Implement chosen AI option (A/B/C from section 8)
- Add config via env:
  - `AI_PROVIDER`, `OPENAI_API_KEY` or other, model name, etc.
- Add fallback behavior if missing keys
- Add tests for deterministic parts (e.g., enrichment parsing, retrieval ranking)

**Exit criteria**
- AI endpoint/feature works end-to-end
- documented in README

---

### Phase 6 — Deployment
**Tasks**
- Add Dockerfile
- Deploy to chosen platform
- Provision managed Postgres
- Set env vars
- Add deployed URL to README

**Exit criteria**
- Live URL reachable
- core flows work on deployed app

---

## 11 Coding standards

- Type hints everywhere reasonable
- Pydantic validation for all inputs
- Consistent error responses
- Keep business logic in `services/`, not in routers
- Write tests for:
  - RBAC boundaries
  - book/loan state transitions
  - search correctness

---

## 12 Commands (must exist and remain correct)

Document and ensure these work:
- `uvicorn app.main:app --reload`
- `pytest`
- `ruff check .`
- `black .`
- `alembic upgrade head`
- `python -m app.db.seed` (or equivalent)

---

## 13 Progress reporting format

After each phase, report:
1) What changed (bullets)
2) How to run/verify (exact commands)
3) Any known limitations / follow-ups