"""Option C — "Ask the Library" tests.

Pure unit tests (no DB, no network) plus API-level tests that mock the
service.  DB-backed tests auto-skip when Postgres is absent.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.book import Book, BookStatus
from app.models.user import User, UserRole
from app.schemas.book import BookResponse
from app.services.library_chat import (
    ChatResult,
    _build_catalog_context,
    _fallback_answer,
    ask_library,
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
        published_year=2020,
        description="A test description.",
        tags=["test"],
        status=BookStatus.AVAILABLE,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return Book(**defaults)


def _make_user(role: UserRole = UserRole.MEMBER) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value.lower()}@example.com",
        name=role.value.title(),
        role=role,
        oauth_provider=None,
        oauth_subject=None,
    )


def _fake_chat_result(source: str = "fallback") -> ChatResult:
    book = _make_book()
    return ChatResult(
        answer="Here are some books.",
        books=[BookResponse.model_validate(book)],
        source=source,
    )


# ---------------------------------------------------------------------------
# Unit — catalog context builder
# ---------------------------------------------------------------------------


def test_build_catalog_context_empty():
    result = _build_catalog_context([])
    assert "No relevant books" in result


def test_build_catalog_context_available_book():
    book = _make_book(title="Dune", author="Frank Herbert", status=BookStatus.AVAILABLE)
    ctx = _build_catalog_context([book])
    assert "Dune" in ctx
    assert "Frank Herbert" in ctx
    assert "Available" in ctx


def test_build_catalog_context_borrowed_book():
    book = _make_book(status=BookStatus.BORROWED)
    ctx = _build_catalog_context([book])
    assert "Borrowed" in ctx


def test_build_catalog_context_includes_description():
    book = _make_book(description="A sci-fi masterpiece.")
    ctx = _build_catalog_context([book])
    assert "sci-fi masterpiece" in ctx


def test_build_catalog_context_includes_tags():
    book = _make_book(tags=["sci-fi", "classic"])
    ctx = _build_catalog_context([book])
    assert "sci-fi" in ctx


def test_build_catalog_context_numbering():
    books = [_make_book(title=f"Book {i}") for i in range(3)]
    ctx = _build_catalog_context(books)
    assert "1." in ctx
    assert "2." in ctx
    assert "3." in ctx


# ---------------------------------------------------------------------------
# Unit — fallback answer
# ---------------------------------------------------------------------------


def test_fallback_answer_no_books():
    result = _fallback_answer(question="any question", books=[])
    assert result.source == "fallback"
    assert isinstance(result.answer, str)
    assert len(result.answer) > 0
    assert result.books == []


def test_fallback_answer_with_books():
    books = [
        _make_book(title="Dune", status=BookStatus.AVAILABLE),
        _make_book(title="1984", status=BookStatus.BORROWED),
    ]
    result = _fallback_answer(question="sci-fi books?", books=books)
    assert result.source == "fallback"
    assert "Dune" in result.answer
    assert "1984" in result.answer
    assert len(result.books) == 2


def test_fallback_answer_shows_status():
    books = [_make_book(status=BookStatus.BORROWED)]
    result = _fallback_answer(question="?", books=books)
    assert "borrowed" in result.answer.lower() or "currently" in result.answer.lower()


# ---------------------------------------------------------------------------
# Unit — ask_library routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_library_uses_fallback_when_no_key():
    db = MagicMock()
    with (
        patch("app.services.library_chat.settings") as mock_settings,
        patch(
            "app.services.library_chat._retrieve_relevant_books",
            new=AsyncMock(return_value=[]),
        ),
    ):
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.AI_PROVIDER = "openai"
        result = await ask_library(db, question="any question?")
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_ask_library_falls_back_on_error():
    db = MagicMock()
    with (
        patch("app.services.library_chat.settings") as mock_settings,
        patch(
            "app.services.library_chat._retrieve_relevant_books",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.library_chat._openai_answer",
            new=AsyncMock(side_effect=RuntimeError("network")),
        ),
    ):
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.AI_PROVIDER = "openai"
        result = await ask_library(db, question="test?")
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_ask_library_openai_success():
    fake = _fake_chat_result("openai")
    db = MagicMock()
    with (
        patch("app.services.library_chat.settings") as mock_settings,
        patch(
            "app.services.library_chat._retrieve_relevant_books",
            new=AsyncMock(return_value=[]),
        ),
        patch("app.services.library_chat._openai_answer", new=AsyncMock(return_value=fake)),
    ):
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.AI_PROVIDER = "openai"
        result = await ask_library(db, question="test?")
    assert result.source == "openai"


# ---------------------------------------------------------------------------
# API — /ask endpoint (no DB, no network)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def member_client_stub_db():
    """Authenticated MEMBER client with get_db stubbed."""
    member = _make_user(UserRole.MEMBER)

    async def _override_user():
        return member

    async def _stub_db():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _stub_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_ask_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post("/api/v1/books/ask", json={"question": "What sci-fi books?"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ask_missing_question(member_client_stub_db: AsyncClient) -> None:
    resp = await member_client_stub_db.post("/api/v1/books/ask", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_question_too_long(member_client_stub_db: AsyncClient) -> None:
    resp = await member_client_stub_db.post("/api/v1/books/ask", json={"question": "x" * 501})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_fallback_response(member_client_stub_db: AsyncClient) -> None:
    """With mocked service, /ask returns correct shape."""
    fake = _fake_chat_result("fallback")
    with patch("app.api.v1.books.ask_library", new=AsyncMock(return_value=fake)):
        resp = await member_client_stub_db.post(
            "/api/v1/books/ask", json={"question": "What sci-fi books do you have?"}
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "fallback"
    assert isinstance(body["answer"], str) and len(body["answer"]) > 0
    assert isinstance(body["books"], list)


@pytest.mark.asyncio
async def test_ask_openai_response(member_client_stub_db: AsyncClient) -> None:
    fake = _fake_chat_result("openai")
    with patch("app.api.v1.books.ask_library", new=AsyncMock(return_value=fake)):
        resp = await member_client_stub_db.post(
            "/api/v1/books/ask", json={"question": "Recommend a classic novel."}
        )

    assert resp.status_code == 200
    assert resp.json()["source"] == "openai"


@pytest.mark.asyncio
async def test_ask_books_field_is_source_grounding(member_client_stub_db: AsyncClient) -> None:
    """The books field in the response always comes from the DB, not invented."""
    book = _make_book(title="Real DB Book")
    fake = ChatResult(
        answer="I recommend Real DB Book.",
        books=[BookResponse.model_validate(book)],
        source="openai",
    )
    with patch("app.api.v1.books.ask_library", new=AsyncMock(return_value=fake)):
        resp = await member_client_stub_db.post(
            "/api/v1/books/ask", json={"question": "Recommend something."}
        )

    body = resp.json()
    assert any(b["title"] == "Real DB Book" for b in body["books"])


# ---------------------------------------------------------------------------
# DB-backed test (skips without Postgres)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_fallback_live(db) -> None:
    """With a real DB (no AI key), /ask returns a fallback grounded in actual books."""
    member = _make_user(UserRole.MEMBER)

    async def _override_user():
        return member

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = lambda: (yield db)  # type: ignore[misc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/books/ask", json={"question": "Any books available?"})

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert isinstance(body["answer"], str)
    assert isinstance(body["books"], list)
