from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.api.v1.health import router as health_router
from app.api.v1.loans import router as loans_router
from app.core.config import settings
from app.core.logging import setup_logging

_TAG_METADATA: list[dict[str, Any]] = [
    {
        "name": "health",
        "description": "Server liveness probe. No authentication required.",
    },
    {
        "name": "auth",
        "description": (
            "OAuth 2.0 SSO login via **Google** or **GitHub**.\n\n"
            "After completing the login flow, open your browser Developer Tools → "
            "Application → Local Storage and copy the value stored under "
            "`access_token`.\n\n"
            "Pass it in every protected request:\n\n"
            "```\nAuthorization: Bearer <token>\n```\n\n"
            "Click the **Authorize** button at the top of this page and paste "
            "your token to unlock all authenticated endpoints directly in Swagger UI."
        ),
    },
    {
        "name": "books",
        "description": (
            "Full CRUD for the book catalogue plus text search and pagination.\n\n"
            "- **GET** endpoints are **public** — no token required.\n"
            "- **POST / PUT / DELETE** require **Librarian** or **Admin** role."
        ),
    },
    {
        "name": "loans",
        "description": (
            "Check-out and return workflows.\n\n"
            "- Any authenticated user may borrow an available book.\n"
            "- **Members** may only return their **own** loans.\n"
            "- **Librarians** and **Admins** may return any loan.\n\n"
            "> **Business rule:** a book can have **at most one active loan** at a time. "
            "Attempting to borrow an already-borrowed book returns `409 Conflict`."
        ),
    },
    {
        "name": "ai",
        "description": (
            "Three AI-powered features, all backed by OpenAI with **graceful fallback** "
            "to deterministic heuristics when `OPENAI_API_KEY` is not configured.\n\n"
            "| Endpoint | Description | Auth |\n"
            "|----------|-------------|------|\n"
            "| `POST /books/enrich` | Generate summary, tags & keywords before saving | Librarian / Admin |\n"
            "| `GET /books/ai-search` | Rank books by embedding similarity | Public |\n"
            "| `POST /books/ask` | Grounded library chat assistant | Any authenticated user |\n\n"
            "The `source` field in every AI response tells you whether OpenAI or the "
            "fallback was used."
        ),
    },
    {
        "name": "admin",
        "description": (
            "User management. Restricted to **Admin** role only.\n\n"
            "New OAuth users are created as **Member**. "
            "Use `PATCH /admin/users/{id}/role` to promote them to Librarian or Admin."
        ),
    },
]

_APP_DESCRIPTION = """\
A **Mini Library Management System** built with FastAPI, PostgreSQL, and OpenAI.

## Authentication

All protected endpoints require a **Bearer JWT** obtained through the OAuth login flow:

1. Open `GET /api/v1/auth/login/google` (or `/github`) in your **browser**.
2. Complete the OAuth consent screen.
3. After login, open your browser Developer Tools → Application → Local Storage.
4. Copy the value stored under `access_token`.
5. Paste the token into the **Authorize** dialog (🔒 button above).

Every protected endpoint then works directly from this Swagger UI.

## Roles & Permissions

| Role | Capabilities |
|------|--------------|
| **Admin** | Full access including user management |
| **Librarian** | Create / edit / delete books; manage all loans |
| **Member** | Browse and search books; borrow and return **own** loans |

New OAuth users start as **Member**. An Admin must promote them via\
 `PATCH /api/v1/admin/users/{id}/role`.

## AI Features

All three AI endpoints degrade gracefully — they never return an error due to\
 missing AI configuration. Check the `source` field (`"openai"` vs `"fallback"`) to\
 see which path was taken.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield


app = FastAPI(
    title="Library Management System",
    description=_APP_DESCRIPTION,
    version="0.1.0",
    openapi_tags=_TAG_METADATA,
    contact={
        "name": "Library Management System",
        "url": "https://github.com/maherabbass/Library-Management-System",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# CORS — explicit origins + optional regex for dynamic URLs (e.g. Netlify previews)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (OAuth)
# Production (HTTPS): SameSite=none + Secure so the cookie is sent back on the
# cross-site redirect from Google/GitHub to our callback URL.
# Development (HTTP): SameSite=lax (browsers reject SameSite=none without Secure).
_prod = settings.APP_ENV == "production"
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    same_site="none" if _prod else "lax",
    https_only=_prod,
)

# Routers
app.include_router(health_router)
app.include_router(books_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(loans_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Custom OpenAPI schema — injects BearerAuth security scheme so the
# "Authorize" button works correctly in Swagger UI and ReDoc.
# ---------------------------------------------------------------------------


def _custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema  # type: ignore[return-value]

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        tags=app.openapi_tags,
        contact=app.contact,
        license_info=app.license_info,
        routes=app.routes,
    )

    # Register the BearerAuth security scheme
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": (
            "JWT access token obtained from `GET /api/v1/auth/callback/{provider}`. "
            "Obtain it by completing the OAuth login flow and copying the `token` "
            "query parameter from the redirect URL."
        ),
    }

    app.openapi_schema = schema  # type: ignore[assignment]
    return schema  # type: ignore[return-value]


app.openapi = _custom_openapi  # type: ignore[method-assign]
