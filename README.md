# Mini Library Management System

A full-featured Library Management System built with **FastAPI**, **PostgreSQL**, **OAuth SSO**, and **AI-powered features**.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12+) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x async + asyncpg |
| Migrations | Alembic |
| Auth | Authlib (OAuth2) + python-jose (JWT) |
| AI | OpenAI API |
| Lint/Format | ruff + black |
| Tests | pytest + httpx |

## Local Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- (Optional) `uv` or `pip` for dependency management

### 1. Clone & configure

```bash
git clone <repo-url>
cd Library-Management-System
cp .env.example .env
# Edit .env with your secrets
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. (Optional) Seed the database

```bash
python -m app.db.seed
```

### 6. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

## Commands

| Command | Purpose |
|---|---|
| `uvicorn app.main:app --reload` | Start dev server |
| `pytest` | Run tests |
| `ruff check .` | Lint |
| `black .` | Format |
| `alembic upgrade head` | Apply migrations |
| `alembic revision --autogenerate -m "desc"` | Generate migration |
| `python -m app.db.seed` | Seed database |
| `docker compose up -d` | Start Postgres |
| `docker compose down` | Stop Postgres |

## Environment Variables

See `.env.example` for all required variables.

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret |
| `DATABASE_URL` | Async PostgreSQL connection string |
| `GOOGLE_CLIENT_ID/SECRET` | Google OAuth credentials |
| `GITHUB_CLIENT_ID/SECRET` | GitHub OAuth credentials |
| `FRONTEND_URL` | Frontend origin for CORS |
| `OPENAI_API_KEY` | OpenAI API key (AI features) |

## API Endpoints

Base URL: `/api/v1`

### Auth
- `GET /api/v1/auth/login/{provider}` — Start OAuth flow
- `GET /api/v1/auth/callback/{provider}` — OAuth callback
- `GET /api/v1/auth/me` — Current user info

### Books
- `GET /api/v1/books` — List books (with search & pagination)
- `POST /api/v1/books` — Create book (Librarian/Admin)
- `GET /api/v1/books/{id}` — Get book
- `PUT /api/v1/books/{id}` — Update book (Librarian/Admin)
- `DELETE /api/v1/books/{id}` — Delete book (Librarian/Admin)
- `GET /api/v1/books/ai-search` — Semantic search (AI)

### Loans
- `POST /api/v1/loans/checkout` — Borrow a book
- `POST /api/v1/loans/return` — Return a book
- `GET /api/v1/loans` — List loans

### Admin
- `GET /api/v1/admin/users` — List users (Admin)
- `PATCH /api/v1/admin/users/{id}/role` — Change user role (Admin)

### Health
- `GET /health` — Health check

## Roles & Permissions

| Role | Permissions |
|---|---|
| **Admin** | Full access including user management |
| **Librarian** | Create/edit/delete books, manage all loans |
| **Member** | View/search books, borrow/return own loans |

## Deployment

> Deployment details will be added after Phase 6.

- **Backend:** Render
- **Database:** Render managed PostgreSQL
- **Live URL:** _TBD_
