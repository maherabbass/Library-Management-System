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
| `BACKEND_URL` | Public backend URL used to build OAuth callback URIs |
| `AI_PROVIDER` | AI backend to use (`openai` — the only supported value) |
| `OPENAI_API_KEY` | OpenAI API key; leave empty to use deterministic fallback |
| `OPENAI_MODEL` | OpenAI model name (default: `gpt-4o-mini`) |

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
- `POST /api/v1/books/enrich` — AI metadata enrichment (Librarian/Admin)

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

## AI Enrichment Feature

`POST /api/v1/books/enrich` generates summary, tags, and keywords for a book
given its title, author, and optional description.  Librarians call it to
preview metadata before creating or updating a book — nothing is saved
automatically.

```bash
TOKEN="<librarian access token>"

curl -X POST http://localhost:8000/api/v1/books/enrich \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title":"Dune","author":"Frank Herbert","description":"A sci-fi epic set on a desert planet."}'
```

Example response with OpenAI configured:
```json
{
  "summary": "A science fiction epic following Paul Atreides on the desert planet Arrakis.",
  "tags": ["science-fiction", "epic", "desert"],
  "keywords": ["dune", "arrakis", "spice", "paul", "atreides", "herbert"],
  "source": "openai"
}
```

Example response **without** `OPENAI_API_KEY` (deterministic fallback):
```json
{
  "summary": "A sci-fi epic set on a desert planet.",
  "tags": ["dune", "frank", "herbert"],
  "keywords": ["dune", "frank", "herbert"],
  "source": "fallback"
}
```

To enable OpenAI: set `OPENAI_API_KEY` in `.env`.  Any provider errors also
fall back gracefully to the heuristic enrichment.

## OAuth Setup (Local Development)

To test Google or GitHub SSO locally:

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add Authorized redirect URI: `http://localhost:8000/api/v1/auth/callback/google`
4. Copy Client ID + Secret into `.env`

### GitHub OAuth
1. Go to GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. Set Authorization callback URL: `http://localhost:8000/api/v1/auth/callback/github`
3. Copy Client ID + Secret into `.env`

### Testing OAuth flow
```bash
# Start server
uvicorn app.main:app --reload

# Open browser:
# http://localhost:8000/api/v1/auth/login/google
# (redirects → OAuth consent → returns {"access_token": "...", "token_type": "bearer"})

# Use the token:
TOKEN="<paste_access_token>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/users  # Admin only
```

## Deployment

### Architecture

| Component | Technology |
|---|---|
| Backend runtime | Google Cloud Run (managed, serverless) |
| Database | Google Cloud SQL — PostgreSQL 16 |
| Container registry | Google Artifact Registry |
| CI/CD | GitHub Actions |
| Auth (CI/CD) | Workload Identity Federation (OIDC — no JSON keys) |
| Migrations | Cloud Run Job (`alembic upgrade head`) |

**Live URL:** `https://library-app-<hash>-ew.a.run.app` _(printed at the end of every GitHub Actions deploy run)_

---

### One-time GCP setup

Run these commands **once** from any machine with `gcloud` authenticated as project Owner.
Replace `GITHUB_ORG` / `GITHUB_REPO` if you forked the repo.

```bash
PROJECT_ID="library-system-488110-p7"
REGION="europe-west1"
GITHUB_ORG="maherabbass"
GITHUB_REPO="Library-Management-System"
SA_NAME="github-actions-sa"
WIF_POOL="github-pool"
WIF_PROVIDER_NAME="github-provider"

# 1 — Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project=$PROJECT_ID

# 2 — Create Artifact Registry Docker repository
gcloud artifacts repositories create library-app \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID

# 3 — Create dedicated service account for GitHub Actions
gcloud iam service-accounts create $SA_NAME \
  --display-name="GitHub Actions Deploy SA" \
  --project=$PROJECT_ID

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 4 — Grant the minimum required IAM roles
for ROLE in \
  roles/run.admin \
  roles/artifactregistry.writer \
  roles/cloudsql.client \
  roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE"
done

# 5 — Create Workload Identity Pool
gcloud iam workload-identity-pools create $WIF_POOL \
  --location=global \
  --display-name="GitHub Actions Pool" \
  --project=$PROJECT_ID

POOL_ID=$(gcloud iam workload-identity-pools describe $WIF_POOL \
  --location=global \
  --project=$PROJECT_ID \
  --format="value(name)")

# 6 — Create OIDC provider (scoped to this exact repo)
gcloud iam workload-identity-pools providers create-oidc $WIF_PROVIDER_NAME \
  --location=global \
  --workload-identity-pool=$WIF_POOL \
  --display-name="GitHub OIDC Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository=='${GITHUB_ORG}/${GITHUB_REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --project=$PROJECT_ID

PROVIDER_ID=$(gcloud iam workload-identity-pools providers describe $WIF_PROVIDER_NAME \
  --location=global \
  --workload-identity-pool=$WIF_POOL \
  --project=$PROJECT_ID \
  --format="value(name)")

# 7 — Allow the repo's OIDC token to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}" \
  --project=$PROJECT_ID

# 8 — Print the values you need for GitHub Secrets (step below)
echo ""
echo "=== Add these as GitHub Secrets ==="
echo "WIF_PROVIDER:       ${PROVIDER_ID}"
echo "GCP_SERVICE_ACCOUNT: ${SA_EMAIL}"
```

---

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name | Value | Notes |
|---|---|---|
| `WIF_PROVIDER` | output of step 8 above | WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | output of step 8 above | SA email |
| `DATABASE_URL` | see format below | Cloud SQL async URL |
| `SECRET_KEY` | random 32+ char string | JWT signing key |
| `GOOGLE_CLIENT_ID` | from Google Cloud Console | OAuth 2.0 client |
| `GOOGLE_CLIENT_SECRET` | from Google Cloud Console | OAuth 2.0 secret |
| `GH_CLIENT_ID` | from GitHub OAuth App | **note: cannot start with `GITHUB_`** |
| `GH_CLIENT_SECRET` | from GitHub OAuth App | same note |
| `FRONTEND_URL` | e.g. `https://your-frontend.vercel.app` | or same as BACKEND_URL |
| `BACKEND_URL` | your Cloud Run service URL | update after first deploy |
| `OPENAI_API_KEY` | OpenAI key | leave empty to use fallback |

#### DATABASE_URL format for Cloud SQL (Unix socket)

Cloud Run connects to Cloud SQL via a Unix socket automatically when
`--add-cloudsql-instances` is set. Use this URL format:

```
postgresql+asyncpg://DB_USER:DB_PASSWORD@/DB_NAME?host=/cloudsql/library-system-488110-p7:europe-west1:library-postgres
```

> **Note:** if your password contains a comma, URL-encode it (`,` → `%2C`).

---

### OAuth callback URLs (production)

After you know your Cloud Run URL, update your OAuth app registrations:

| Provider | Callback URL |
|---|---|
| Google | `https://<cloud-run-url>/api/v1/auth/callback/google` |
| GitHub | `https://<cloud-run-url>/api/v1/auth/callback/github` |

Set `BACKEND_URL=https://<cloud-run-url>` in GitHub Secrets so the app
generates the correct redirect URIs.

---

### How the CI/CD pipeline works

```
push to main
  └─ test job: ruff + black --check + pytest (no DB needed)
       └─ deploy job (main only):
            1. WIF auth (OIDC, no keys)
            2. docker build + push → Artifact Registry
            3. Cloud Run Job: alembic upgrade head  ← migrations BEFORE traffic
            4. gcloud run deploy → new revision gets 100% traffic
            5. Print live URL
```

**Migration order justification:** additive migrations (adding tables / columns)
are safe for the currently-running code. Running them *before* the new revision
goes live means the schema is ready the moment new traffic arrives, with zero
risk of the old code breaking.

---

### Getting the deployed URL

The URL is printed at the end of each deploy run ("Print deployed URL" step).
You can also query it any time:

```bash
gcloud run services describe library-app \
  --region=europe-west1 \
  --project=library-system-488110-p7 \
  --format="value(status.url)"
```

---

### Verify the deployed app

```bash
BASE="https://<your-cloud-run-url>"

# Health check
curl "$BASE/health"
# → {"status":"ok","version":"0.1.0"}

# List books (public)
curl "$BASE/api/v1/books"

# Interactive docs
open "$BASE/docs"
```
