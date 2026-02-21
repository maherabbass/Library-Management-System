"""Phase 5 — AI enrichment tests.

All tests run without a database.
Network calls to OpenAI are mocked where needed.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.user import User, UserRole
from app.services.ai import EnrichmentResult, _fallback_enrich, enrich_book_metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value.lower()}@example.com",
        name=role.value.title(),
        role=role,
        oauth_provider=None,
        oauth_subject=None,
    )


@pytest_asyncio.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def librarian_client():
    librarian = _make_user(UserRole.LIBRARIAN)

    async def _override():
        return librarian

    app.dependency_overrides[get_current_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def member_client():
    member = _make_user(UserRole.MEMBER)

    async def _override():
        return member

    app.dependency_overrides[get_current_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Unit tests — fallback enrichment (no network, no DB)
# ---------------------------------------------------------------------------


def test_fallback_returns_correct_shape():
    result = _fallback_enrich("The Great Gatsby", "F. Scott Fitzgerald", None)
    assert isinstance(result, EnrichmentResult)
    assert isinstance(result.summary, str)
    assert len(result.summary) > 0
    assert isinstance(result.tags, list)
    assert isinstance(result.keywords, list)
    assert result.source == "fallback"


def test_fallback_is_deterministic():
    r1 = _fallback_enrich("Dune", "Frank Herbert", "A sci-fi epic.")
    r2 = _fallback_enrich("Dune", "Frank Herbert", "A sci-fi epic.")
    assert r1.summary == r2.summary
    assert r1.tags == r2.tags
    assert r1.keywords == r2.keywords


def test_fallback_uses_description_as_summary():
    desc = "An exploration of power and ecology."
    result = _fallback_enrich("Dune", "Frank Herbert", desc)
    assert desc in result.summary


def test_fallback_generates_summary_without_description():
    result = _fallback_enrich("1984", "George Orwell", None)
    assert "Orwell" in result.summary or "1984" in result.summary


def test_fallback_tags_contain_title_words():
    result = _fallback_enrich("Brave New World", "Aldous Huxley", None)
    all_terms = set(result.tags) | set(result.keywords)
    # At least one meaningful word from the title should appear
    assert any(w in all_terms for w in ["brave", "world", "huxley"])


def test_fallback_tags_respect_max_count():
    result = _fallback_enrich("The Very Long Title With Many Words Here", "Author Name", None)
    assert len(result.tags) <= 5
    assert len(result.keywords) <= 7


def test_fallback_stopwords_excluded():
    result = _fallback_enrich("The Book", "The Author", None)
    for term in result.tags + result.keywords:
        assert term not in {"the", "a", "an", "and", "or"}


# ---------------------------------------------------------------------------
# Unit tests — enrich_book_metadata routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_metadata_uses_fallback_when_key_missing():
    """With no API key configured, enrich_book_metadata returns fallback."""
    with patch("app.services.ai._is_ai_configured", return_value=False):
        result = await enrich_book_metadata("Hamlet", "Shakespeare")
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_enrich_metadata_falls_back_on_openai_error():
    """If OpenAI raises, enrich_book_metadata returns fallback instead of propagating."""
    with (
        patch("app.services.ai._is_ai_configured", return_value=True),
        patch("app.services.ai._openai_enrich", side_effect=RuntimeError("network error")),
    ):
        result = await enrich_book_metadata("Test", "Author")
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_enrich_metadata_openai_success():
    """When OpenAI succeeds, enrich_book_metadata returns its result."""
    fake_result = EnrichmentResult(
        summary="A great story.",
        tags=["fiction", "classic"],
        keywords=["story", "great"],
        source="openai",
    )
    with (
        patch("app.services.ai._is_ai_configured", return_value=True),
        patch("app.services.ai._openai_enrich", new=AsyncMock(return_value=fake_result)),
    ):
        result = await enrich_book_metadata("Test", "Author")
    assert result.source == "openai"
    assert result.summary == "A great story."


# ---------------------------------------------------------------------------
# API boundary tests — auth / RBAC (no DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_endpoint_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post("/api/v1/books/enrich", json={"title": "T", "author": "A"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_enrich_endpoint_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.post("/api/v1/books/enrich", json={"title": "T", "author": "A"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# API integration — fallback path (no DB, no network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_endpoint_fallback_response(librarian_client: AsyncClient) -> None:
    """With no AI key configured, /books/enrich returns deterministic fallback."""
    with patch("app.services.ai._is_ai_configured", return_value=False):
        resp = await librarian_client.post(
            "/api/v1/books/enrich",
            json={"title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "fallback"
    assert isinstance(body["summary"], str) and len(body["summary"]) > 0
    assert isinstance(body["tags"], list)
    assert isinstance(body["keywords"], list)


@pytest.mark.asyncio
async def test_enrich_endpoint_with_description(librarian_client: AsyncClient) -> None:
    desc = "A dystopian tale of surveillance and control."
    with patch("app.services.ai._is_ai_configured", return_value=False):
        resp = await librarian_client.post(
            "/api/v1/books/enrich",
            json={"title": "1984", "author": "George Orwell", "description": desc},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert desc in body["summary"]


@pytest.mark.asyncio
async def test_enrich_endpoint_missing_required_fields(librarian_client: AsyncClient) -> None:
    resp = await librarian_client.post("/api/v1/books/enrich", json={"title": "Only Title"})
    assert resp.status_code == 422  # missing author


@pytest.mark.asyncio
async def test_enrich_endpoint_openai_mocked(librarian_client: AsyncClient) -> None:
    """Verify the OpenAI success path via a mocked client."""
    fake_json = json.dumps(
        {
            "summary": "A mocked AI summary.",
            "tags": ["ai", "mock"],
            "keywords": ["artificial", "intelligence"],
        }
    )
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = fake_json

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with (
        patch("app.services.ai._is_ai_configured", return_value=True),
        patch("app.services.ai.AsyncOpenAI", return_value=mock_client),
    ):
        resp = await librarian_client.post(
            "/api/v1/books/enrich",
            json={"title": "AI Book", "author": "Robot Author"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "openai"
    assert body["summary"] == "A mocked AI summary."
    assert "ai" in body["tags"]
    assert "artificial" in body["keywords"]
