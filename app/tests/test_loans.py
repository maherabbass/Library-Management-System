"""Phase 4 — Loan tests.

No-DB tests  : 401 boundary checks (always run).
DB tests     : full business-rule tests; skip gracefully if Postgres absent.
"""

import contextlib
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.book import Book, BookStatus
from app.models.loan import LoanStatus
from app.models.user import User, UserRole
from app.services.loan import checkout_book, return_book

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _create_user(db, *, role: UserRole = UserRole.MEMBER) -> User:
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        role=role,
        oauth_provider=None,
        oauth_subject=None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_book(db, *, status: BookStatus = BookStatus.AVAILABLE) -> Book:
    book = Book(
        title=f"Test Book {uuid.uuid4().hex[:6]}",
        author="Test Author",
        status=status,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


@contextlib.asynccontextmanager
async def _client_as(user: User, db):
    """HTTP client authenticated as *user*, using the test DB session."""

    async def _override_user():
        return user

    async def _override_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# No-DB boundary tests (always run)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_checkout_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post("/api/v1/loans/checkout", json={"book_id": str(uuid.uuid4())})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_return_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post("/api/v1/loans/return", json={"loan_id": str(uuid.uuid4())})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_loans_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/loans")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DB-required tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_available_book(db) -> None:
    """Checking out an AVAILABLE book succeeds and marks it BORROWED."""
    user = await _create_user(db)
    book = await _create_book(db)

    async with _client_as(user, db) as ac:
        resp = await ac.post("/api/v1/loans/checkout", json={"book_id": str(book.id)})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["book_id"] == str(book.id)
    assert body["user_id"] == str(user.id)
    assert body["status"] == "OUT"
    assert body["returned_at"] is None

    # Book should now be BORROWED in the DB
    await db.refresh(book)
    assert book.status == BookStatus.BORROWED


@pytest.mark.asyncio
async def test_checkout_borrowed_book_fails(db) -> None:
    """Attempting to checkout a BORROWED book returns 409."""
    user = await _create_user(db)
    book = await _create_book(db)

    # First checkout succeeds
    async with _client_as(user, db) as ac:
        resp = await ac.post("/api/v1/loans/checkout", json={"book_id": str(book.id)})
    assert resp.status_code == 201

    # Second checkout of same book → 409
    user2 = await _create_user(db)
    async with _client_as(user2, db) as ac:
        resp = await ac.post("/api/v1/loans/checkout", json={"book_id": str(book.id)})
    assert resp.status_code == 409
    assert "already borrowed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_checkout_nonexistent_book(db) -> None:
    user = await _create_user(db)
    async with _client_as(user, db) as ac:
        resp = await ac.post("/api/v1/loans/checkout", json={"book_id": str(uuid.uuid4())})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_return_own_loan_member(db) -> None:
    """A MEMBER can return their own active loan."""
    user = await _create_user(db, role=UserRole.MEMBER)
    book = await _create_book(db)
    loan = await checkout_book(db, book_id=book.id, current_user=user)

    async with _client_as(user, db) as ac:
        resp = await ac.post("/api/v1/loans/return", json={"loan_id": str(loan.id)})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "RETURNED"
    assert body["returned_at"] is not None

    await db.refresh(book)
    assert book.status == BookStatus.AVAILABLE


@pytest.mark.asyncio
async def test_return_other_users_loan_member_forbidden(db) -> None:
    """A MEMBER cannot return another user's loan."""
    owner = await _create_user(db, role=UserRole.MEMBER)
    other = await _create_user(db, role=UserRole.MEMBER)
    book = await _create_book(db)
    loan = await checkout_book(db, book_id=book.id, current_user=owner)

    async with _client_as(other, db) as ac:
        resp = await ac.post("/api/v1/loans/return", json={"loan_id": str(loan.id)})

    assert resp.status_code == 403
    assert "another user" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_return_any_loan_librarian(db) -> None:
    """A LIBRARIAN can return any active loan."""
    member = await _create_user(db, role=UserRole.MEMBER)
    librarian = await _create_user(db, role=UserRole.LIBRARIAN)
    book = await _create_book(db)
    loan = await checkout_book(db, book_id=book.id, current_user=member)

    async with _client_as(librarian, db) as ac:
        resp = await ac.post("/api/v1/loans/return", json={"loan_id": str(loan.id)})

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_return_any_loan_admin(db) -> None:
    """An ADMIN can return any active loan."""
    member = await _create_user(db, role=UserRole.MEMBER)
    admin = await _create_user(db, role=UserRole.ADMIN)
    book = await _create_book(db)
    loan = await checkout_book(db, book_id=book.id, current_user=member)

    async with _client_as(admin, db) as ac:
        resp = await ac.post("/api/v1/loans/return", json={"loan_id": str(loan.id)})

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_return_nonexistent_loan(db) -> None:
    user = await _create_user(db)
    async with _client_as(user, db) as ac:
        resp = await ac.post("/api/v1/loans/return", json={"loan_id": str(uuid.uuid4())})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_loans_member_sees_own_only(db) -> None:
    """MEMBER list returns only their own loans."""
    member1 = await _create_user(db, role=UserRole.MEMBER)
    member2 = await _create_user(db, role=UserRole.MEMBER)
    book1 = await _create_book(db)
    book2 = await _create_book(db)

    await checkout_book(db, book_id=book1.id, current_user=member1)
    await checkout_book(db, book_id=book2.id, current_user=member2)

    async with _client_as(member1, db) as ac:
        resp = await ac.get("/api/v1/loans")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    user_ids = {item["user_id"] for item in body["items"]}
    assert user_ids == {str(member1.id)}, f"Expected only member1 loans, got user_ids={user_ids}"


@pytest.mark.asyncio
async def test_list_loans_librarian_sees_all(db) -> None:
    """LIBRARIAN list includes loans from all users."""
    member1 = await _create_user(db, role=UserRole.MEMBER)
    member2 = await _create_user(db, role=UserRole.MEMBER)
    librarian = await _create_user(db, role=UserRole.LIBRARIAN)
    book1 = await _create_book(db)
    book2 = await _create_book(db)

    await checkout_book(db, book_id=book1.id, current_user=member1)
    await checkout_book(db, book_id=book2.id, current_user=member2)

    async with _client_as(librarian, db) as ac:
        resp = await ac.get("/api/v1/loans")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    user_ids = {item["user_id"] for item in body["items"]}
    # Both members' loans must be visible
    assert str(member1.id) in user_ids
    assert str(member2.id) in user_ids


@pytest.mark.asyncio
async def test_double_checkout_prevented_by_service(db) -> None:
    """
    Transactional correctness: calling checkout_book twice for the same book
    raises a 409 on the second call (caught at status-check or unique-index level).
    """
    user = await _create_user(db)
    book = await _create_book(db)

    # First checkout via service directly
    loan = await checkout_book(db, book_id=book.id, current_user=user)
    assert loan.status == LoanStatus.OUT

    # Second call must raise HTTPException(409)
    with pytest.raises(HTTPException) as exc_info:
        await checkout_book(db, book_id=book.id, current_user=user)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_book_available_again_after_return(db) -> None:
    """After return, book can be checked out again by another user."""
    user1 = await _create_user(db)
    user2 = await _create_user(db)
    book = await _create_book(db)

    loan = await checkout_book(db, book_id=book.id, current_user=user1)
    await return_book(db, loan_id=loan.id, current_user=user1)

    # Now user2 can check it out
    loan2 = await checkout_book(db, book_id=book.id, current_user=user2)
    assert loan2.status == LoanStatus.OUT
    assert loan2.user_id == user2.id
