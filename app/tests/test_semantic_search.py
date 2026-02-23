"""Option B — Semantic search tests.

Pure unit tests (no DB, no network) plus API-level tests that mock the
service function so no DB connection is needed.
DB-backed tests auto-skip when Postgres is absent.
"""

import math
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.book import Book, BookStatus
from app.schemas.book import BookResponse
from app.services.semantic_search import (
    SemanticSearchResult,
    _book_text,
    _cosine_similarity,
    semantic_book_search,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_book(**kwargs) -> Book:
    defaults = dict(
        id=uuid.uuid4(),
        title="Test Book",
        author="Test Author",
        isbn=None,
        published_year=None,
        description=None,
        tags=None,
        status=BookStatus.AVAILABLE,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return Book(**defaults)


def _fake_result(source: str = "fallback") -> SemanticSearchResult:
    book = _make_book(title="Dune", author="Frank Herbert")
    return SemanticSearchResult(
        items=[BookResponse.model_validate(book)],
        total=1,
        source=source,
        query="desert planet",
    )


# ---------------------------------------------------------------------------
# Unit — cosine similarity
# ---------------------------------------------------------------------------


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert math.isclose(_cosine_similarity(v, v), 1.0)


def test_cosine_similarity_opposite():
    assert math.isclose(_cosine_similarity([1.0, 0.0], [-1.0, 0.0]), -1.0)


def test_cosine_similarity_orthogonal():
    assert math.isclose(_cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)


def test_cosine_similarity_zero_vector():
    assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_similarity_known_value():
    # [1,1] vs [1,0] → dot=1, norms=√2 and 1 → 1/√2 ≈ 0.707
    result = _cosine_similarity([1.0, 1.0], [1.0, 0.0])
    assert math.isclose(result, 1.0 / math.sqrt(2), rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Unit — book text construction
# ---------------------------------------------------------------------------


def test_book_text_title_and_author():
    book = _make_book(title="Dune", author="Frank Herbert")
    text = _book_text(book)
    assert "Dune" in text
    assert "Frank Herbert" in text


def test_book_text_includes_description():
    book = _make_book(description="A sci-fi epic.")
    assert "sci-fi epic" in _book_text(book)


def test_book_text_includes_tags():
    book = _make_book(tags=["sci-fi", "desert"])
    assert "sci-fi" in _book_text(book)
    assert "desert" in _book_text(book)


def test_book_text_no_description_no_tags():
    book = _make_book(description=None, tags=None)
    text = _book_text(book)
    # Should still have title and author
    assert book.title in text
    assert book.author in text


# ---------------------------------------------------------------------------
# Unit — semantic_book_search routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_search_uses_fallback_when_no_key():
    with patch("app.services.semantic_search.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.AI_PROVIDER = "openai"
        db = MagicMock()
        with patch(
            "app.services.semantic_search._fallback_search",
            new=AsyncMock(return_value=_fake_result("fallback")),
        ):
            result = await semantic_book_search(db, query="desert")
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_semantic_search_falls_back_on_error():
    with patch("app.services.semantic_search.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.AI_PROVIDER = "openai"
        db = MagicMock()
        with (
            patch(
                "app.services.semantic_search._openai_search",
                new=AsyncMock(side_effect=RuntimeError("network")),
            ),
            patch(
                "app.services.semantic_search._fallback_search",
                new=AsyncMock(return_value=_fake_result("fallback")),
            ),
        ):
            result = await semantic_book_search(db, query="desert")
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_semantic_search_openai_success():
    with patch("app.services.semantic_search.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.AI_PROVIDER = "openai"
        db = MagicMock()
        with patch(
            "app.services.semantic_search._openai_search",
            new=AsyncMock(return_value=_fake_result("openai")),
        ):
            result = await semantic_book_search(db, query="desert")
    assert result.source == "openai"


# ---------------------------------------------------------------------------
# API — /ai-search endpoint (no DB, no network)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def stub_db_client():
    """Anonymous client with get_db stubbed to avoid DB connections."""

    async def _stub():
        yield MagicMock()

    app.dependency_overrides[get_db] = _stub
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_ai_search_missing_query(stub_db_client: AsyncClient) -> None:
    resp = await stub_db_client.get("/api/v1/books/ai-search")
    assert resp.status_code == 422  # q is required


@pytest.mark.asyncio
async def test_ai_search_fallback_response(stub_db_client: AsyncClient) -> None:
    """Endpoint returns correct shape with fallback when service is mocked."""
    fake = _fake_result("fallback")
    with patch("app.api.v1.books.semantic_book_search", new=AsyncMock(return_value=fake)):
        resp = await stub_db_client.get("/api/v1/books/ai-search?q=desert+planet")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "fallback"
    assert body["query"] == "desert planet"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)


@pytest.mark.asyncio
async def test_ai_search_openai_response(stub_db_client: AsyncClient) -> None:
    fake = _fake_result("openai")
    with patch("app.api.v1.books.semantic_book_search", new=AsyncMock(return_value=fake)):
        resp = await stub_db_client.get("/api/v1/books/ai-search?q=sci-fi")

    assert resp.status_code == 200
    assert resp.json()["source"] == "openai"


@pytest.mark.asyncio
async def test_ai_search_top_k_param(stub_db_client: AsyncClient) -> None:
    fake = _fake_result()
    with patch(
        "app.api.v1.books.semantic_book_search", new=AsyncMock(return_value=fake)
    ) as mock_fn:
        await stub_db_client.get("/api/v1/books/ai-search?q=test&top_k=5")
        mock_fn.assert_called_once()
        _, kwargs = mock_fn.call_args
        assert kwargs["top_k"] == 5


# ---------------------------------------------------------------------------
# DB-backed test (skips without Postgres)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_search_fallback_live(db) -> None:
    """With a real DB (no AI key), endpoint uses ILIKE and returns results."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        app.dependency_overrides[get_db] = lambda: (yield db)  # type: ignore[misc]
        try:
            resp = await ac.get("/api/v1/books/ai-search?q=the")
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert "items" in body
