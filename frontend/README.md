# Library Management System — Frontend

A React + Vite SPA that exercises every feature of the [Library Management System](https://library-app-qtegugoc4a-ew.a.run.app) backend.

## Live URLs

| Service | URL |
|---------|-----|
| **Backend API** | <https://library-app-qtegugoc4a-ew.a.run.app> |
| **API Docs (Swagger)** | <https://library-app-qtegugoc4a-ew.a.run.app/docs> |
| **Frontend (Netlify)** | <https://library-man-sys.netlify.app> |

---

## Features covered

| Area | Feature |
|------|---------|
| **Auth** | OAuth login via Google / GitHub; JWT stored in localStorage |
| **Books** | List with search (title, author, tag, status), pagination, create, edit, delete |
| **Book detail** | Metadata view, checkout, return, Librarian/Admin actions |
| **Loans** | View own loans (Members) or all loans (Librarian/Admin); return button |
| **AI — Enrich** | `POST /books/enrich` — AI-generated summary, tags & keywords (on create/edit form) |
| **AI — Search** | `GET /books/ai-search` — semantic / natural-language search with OpenAI embeddings |
| **AI — Chat** | `POST /books/ask` — grounded library assistant that cites real DB books |
| **Admin** | User list + role promotion/demotion (`MEMBER` → `LIBRARIAN` → `ADMIN`) |

---

## Tech stack

- **React 18** + **TypeScript**
- **React Router v6**
- **Vite 5** (build tool)
- Plain CSS with CSS variables (no framework)
- Fetch API — no axios

---

## Local development

### Prerequisites
- Node.js 20+
- The backend running at `http://localhost:8000`
  (or set `VITE_API_URL` to the deployed backend)

### Steps

```bash
# 1. Enter the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Copy and configure env
cp .env.example .env
# Edit .env — set VITE_API_URL if needed
# Default: points to the deployed Cloud Run backend

# 4. Start dev server
npm run dev
# → http://localhost:5173
```

### Build for production

```bash
npm run build
# Output: frontend/dist/
```

---

## Deployment to Netlify

### Option A — Automated via GitHub Actions (recommended)

The workflow `.github/workflows/deploy-frontend.yml` builds and deploys on every push to `main` that touches `frontend/`.

**One-time setup:**

1. **Create a Netlify account** at <https://netlify.com>.

2. **Create a new site** (Netlify dashboard → "Add new site" → "Deploy manually" → drag any placeholder).

3. **Get your tokens:**
   - `NETLIFY_AUTH_TOKEN`: Netlify user settings → Applications → Personal access tokens
   - `NETLIFY_SITE_ID`: Site settings → Site information → Site ID

4. **Add GitHub Secrets** (repo → Settings → Secrets → Actions):
   ```
   NETLIFY_AUTH_TOKEN   = <your auth token>
   NETLIFY_SITE_ID      = <your site ID>
   VITE_API_URL         = https://library-app-qtegugoc4a-ew.a.run.app
   ```

5. **Update backend CORS** — add the Netlify URL to the `FRONTEND_URL` env var on Cloud Run:
   ```
   FRONTEND_URL=https://your-site.netlify.app
   ```
   This is needed for:
   - CORS to allow the frontend origin
   - The OAuth callback to redirect back to your SPA

6. Push to `main` — the workflow will build and deploy automatically.
   The deployed URL appears in the GitHub Actions logs and as a PR comment.

---

### Option B — Manual Netlify deploy

```bash
cd frontend
npm install
VITE_API_URL=https://library-app-qtegugoc4a-ew.a.run.app npm run build

# Install Netlify CLI once
npm install -g netlify-cli

# Deploy
netlify deploy --prod --dir dist
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | *(empty — uses same origin)* | Backend base URL (no trailing slash) |

Create a `frontend/.env` file for local overrides:
```env
VITE_API_URL=https://library-app-qtegugoc4a-ew.a.run.app
```

---

## OAuth flow

```
Browser → GET /api/v1/auth/login/google
         → Google OAuth consent
         → GET /api/v1/auth/callback/google (backend)
         → 302 redirect to {FRONTEND_URL}/auth/callback?token=<jwt>
         → SPA stores JWT in localStorage, fetches /auth/me
         → redirect to /books
```

New users are created automatically with the **MEMBER** role.
Admins can promote roles in the `/admin` panel.

---

## Project structure

```
frontend/
├── index.html
├── netlify.toml          ← Netlify build config + SPA redirect rule
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env.example
└── src/
    ├── main.tsx          ← entry point
    ├── App.tsx           ← routes + auth guards
    ├── AuthContext.tsx   ← JWT auth state
    ├── api.ts            ← typed API client (all endpoints)
    ├── types.ts          ← TypeScript interfaces
    ├── index.css         ← global styles
    ├── components/
    │   ├── Navbar.tsx
    │   ├── BookCard.tsx
    │   └── Pagination.tsx
    └── pages/
        ├── Login.tsx         ← Google / GitHub OAuth buttons
        ├── AuthCallback.tsx  ← reads ?token= and stores JWT
        ├── Books.tsx         ← list + search + filters
        ├── BookDetail.tsx    ← view + checkout/return
        ├── CreateEditBook.tsx← create/edit form + AI enrich
        ├── Loans.tsx         ← loan history + return
        ├── AISearch.tsx      ← semantic search
        ├── LibraryChat.tsx   ← grounded chat assistant
        └── Admin.tsx         ← user management + role assignment
```
