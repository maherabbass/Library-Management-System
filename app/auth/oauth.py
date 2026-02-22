import base64
import hashlib
import hmac as _hmac
import secrets
import time

from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

oauth = OAuth()
SUPPORTED_PROVIDERS: set[str] = set()

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        "google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    SUPPORTED_PROVIDERS.add("google")

if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
    oauth.register(
        "github",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )
    SUPPORTED_PROVIDERS.add("github")


# ---------------------------------------------------------------------------
# Stateless OAuth state helpers
#
# Cloud Run (and similar serverless platforms) can strip Set-Cookie headers
# from 302 redirect responses, making Authlib's session-based state storage
# unreliable. These helpers implement HMAC-signed state that is self-verifiable
# without any server-side session, eliminating the dependency on session
# cookies surviving the OAuth redirect round-trip.
# ---------------------------------------------------------------------------


def generate_oauth_state(secret_key: str) -> str:
    """Return a URL-safe, HMAC-signed state token.

    Format (base64url-encoded): ``<random_hex>.<timestamp>.<hmac_sha256>``
    """
    prefix = secrets.token_hex(16)
    ts = str(int(time.time()))
    payload = f"{prefix}.{ts}"
    sig = _hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def verify_oauth_state(state: str, secret_key: str, max_age: int = 600) -> bool:
    """Return True iff *state* was produced by :func:`generate_oauth_state`
    with the same *secret_key* and is not older than *max_age* seconds."""
    try:
        padded = state + "=" * ((4 - len(state) % 4) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        prefix, ts, sig = raw.rsplit(".", 2)
        if int(time.time()) - int(ts) > max_age:
            return False
        payload = f"{prefix}.{ts}"
        expected = _hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return _hmac.compare_digest(sig, expected)
    except Exception:
        return False


def state_to_nonce(state: str) -> str:
    """Derive a deterministic OpenID Connect nonce from a verified state token.

    Because the state is HMAC-protected, the nonce derived from it cannot be
    forged independently. Storing this nonce in the session fallback lets
    Authlib's ID-token nonce validation succeed even when the original session
    cookie was lost.
    """
    return hashlib.sha256(state.encode()).hexdigest()
