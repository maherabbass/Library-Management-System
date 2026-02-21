"""RBAC boundary tests.

No-DB tests: override get_current_user only — never touch Postgres.
DB tests: use `client` fixture (skips if no DB).
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole

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


# ---------------------------------------------------------------------------
# No-DB fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def anon_client():
    """Client with no auth override — all auth deps run normally."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


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
# Books RBAC — no-DB boundary checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_book_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post("/api/v1/books", json={"title": "T", "author": "A"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_book_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.put(f"/api/v1/books/{uuid.uuid4()}", json={"title": "T"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_book_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.delete(f"/api/v1/books/{uuid.uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_book_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.post("/api/v1/books", json={"title": "T", "author": "A"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin RBAC — no-DB boundary checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_list_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.get("/api/v1/admin/users")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_role_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.patch(
        f"/api/v1/admin/users/{uuid.uuid4()}/role", json={"role": "MEMBER"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_update_role_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.patch(
        f"/api/v1/admin/users/{uuid.uuid4()}/role", json={"role": "MEMBER"}
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DB-required tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def librarian_client(db):
    """Librarian client backed by a real DB session."""
    librarian = _make_user(UserRole.LIBRARIAN)

    async def _override_user():
        return librarian

    async def _override_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def admin_client(db):
    """Admin client backed by a real DB session."""
    admin = _make_user(UserRole.ADMIN)

    async def _override_user():
        return admin

    async def _override_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_create_book_librarian_allowed(librarian_client: AsyncClient) -> None:
    resp = await librarian_client.post(
        "/api/v1/books",
        json={"title": "Auth Test Book", "author": "Test Author"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Auth Test Book"


@pytest.mark.asyncio
async def test_admin_list_users_admin_allowed(admin_client: AsyncClient, db) -> None:
    resp = await admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "email" in data[0]
        assert "role" in data[0]


@pytest.mark.asyncio
async def test_admin_update_role_admin_allowed(admin_client: AsyncClient, db) -> None:
    result = await db.scalars(select(User).limit(1))
    target = result.first()
    if target is None:
        pytest.skip("No users in DB")

    resp = await admin_client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "LIBRARIAN"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "LIBRARIAN"
