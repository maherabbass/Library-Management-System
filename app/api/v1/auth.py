import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.auth.oauth import (
    SUPPORTED_PROVIDERS,
    generate_oauth_state,
    oauth,
    verify_oauth_state,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserResponse
from app.services.user import get_or_create_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ALL_PROVIDERS = {"google", "github"}

_AUTH_ERROR_RESPONSES: dict = {
    400: {"description": "Unsupported or unknown OAuth provider."},
    503: {
        "description": "OAuth provider is not configured on this server (missing client credentials)."
    },
}


@router.get(
    "/login/{provider}",
    summary="Start OAuth login",
    description=(
        "Redirects the browser to the OAuth provider's authorization page.\n\n"
        "**Open this URL directly in a browser** — it initiates the OAuth redirect flow. "
        "After the user grants consent the provider calls `/callback/{provider}`, which "
        "issues a JWT and redirects to the frontend.\n\n"
        "Supported providers: `google`, `github`."
    ),
    response_description="302 redirect to the provider's authorization page.",
    status_code=302,
    responses={
        **_AUTH_ERROR_RESPONSES,
    },
)
async def login(provider: str, request: Request) -> None:
    if provider not in _ALL_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' is not configured on this server",
        )
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback/{provider}"
    client = oauth.create_client(provider)
    state = generate_oauth_state(settings.SECRET_KEY)
    return await client.authorize_redirect(request, redirect_uri, state=state)


@router.get(
    "/callback/{provider}",
    response_model=TokenResponse,
    summary="OAuth callback — issues JWT",
    description=(
        "Handles the OAuth provider redirect after the user grants consent.\n\n"
        "This endpoint is called **by the OAuth provider**, not directly by the client. "
        "It exchanges the authorization code for a user profile, creates the user in the "
        "database on first login, then:\n\n"
        "- **With frontend configured:** redirects the browser to "
        "`{FRONTEND_URL}/auth/callback?token=<jwt>` so the SPA can store the token.\n"
        "- **Without frontend (API-only mode):** returns the `TokenResponse` JSON directly.\n\n"
        "The JWT is valid for `ACCESS_TOKEN_EXPIRE_MINUTES` minutes (default: 60)."
    ),
    response_description="JWT Bearer token (or 302 redirect to frontend with `?token=...`).",
    responses={
        302: {"description": "Redirect to frontend SPA with `?token=<jwt>` query parameter."},
        **_AUTH_ERROR_RESPONSES,
    },
)
async def callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if provider not in _ALL_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' is not configured on this server",
        )

    # Verify our HMAC-signed state (CSRF guard) — no session cookie needed.
    state = request.query_params.get("state", "")
    if not verify_oauth_state(state, settings.SECRET_KEY):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback/{provider}"

    # Exchange the authorization code for tokens via direct HTTP calls.
    # This bypasses Authlib's session-based state validation entirely, which
    # is unreliable on Cloud Run (the load balancer can strip Set-Cookie from
    # 302 responses). Our HMAC state above provides the CSRF protection instead.
    async with httpx.AsyncClient() as http:
        if provider == "google":
            token_resp = await http.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            access_token_google = token_resp.json()["access_token"]

            userinfo_resp = await http.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token_google}"},
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()

            email: str = userinfo["email"]
            name: str = userinfo.get("name") or email.split("@")[0]
            subject: str = userinfo["sub"]

        else:  # github
            token_resp = await http.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "code": code,
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            gh_token = token_resp.json().get("access_token", "")

            gh_headers = {
                "Authorization": f"token {gh_token}",
                "Accept": "application/json",
            }
            profile_resp = await http.get("https://api.github.com/user", headers=gh_headers)
            profile_resp.raise_for_status()
            profile = profile_resp.json()

            subject = str(profile["id"])
            name = profile.get("name") or profile.get("login") or "GitHub User"
            email = profile.get("email") or ""

            if not email:
                # GitHub may hide the primary email — fetch from /user/emails
                emails_resp = await http.get(
                    "https://api.github.com/user/emails", headers=gh_headers
                )
                emails_resp.raise_for_status()
                emails = emails_resp.json()
                primary = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                if primary is None:
                    primary = next((e["email"] for e in emails if e.get("verified")), None)
                if primary is None:
                    raise HTTPException(
                        status_code=400,
                        detail="No verified email found in GitHub account",
                    )
                email = primary

    user = await get_or_create_user(db, email=email, name=name, provider=provider, subject=subject)
    access_token = create_access_token({"sub": str(user.id)})

    # Redirect to frontend SPA with the JWT; fall back to JSON for API-only usage
    if settings.FRONTEND_URL:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}")
    return TokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description=(
        "Returns the profile of the currently authenticated user decoded from the Bearer token.\n\n"
        "Use this endpoint to:\n"
        "- Verify a token is valid.\n"
        "- Retrieve the user's `id`, `email`, `name`, `role`, and `oauth_provider`.\n\n"
        "**Requires:** `Authorization: Bearer <token>`"
    ),
    response_description="The authenticated user's profile.",
    responses={
        401: {"description": "Missing, invalid, or expired Bearer token."},
    },
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
