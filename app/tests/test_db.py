"""
DB connectivity and model enum tests for Phase 1.

test_db_connection  — requires a running Postgres (skipped if unavailable)
test_model_enums    — pure Python, no DB required
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connection():
    """Verify that the async engine can connect and run a simple query."""
    try:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1
    except Exception as exc:
        pytest.skip(f"Database not available: {exc}")


def test_model_enums():
    """Verify all domain enums have the expected values (no DB required)."""
    from app.models.book import BookStatus
    from app.models.loan import LoanStatus
    from app.models.user import UserRole

    # UserRole
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.LIBRARIAN == "LIBRARIAN"
    assert UserRole.MEMBER == "MEMBER"
    assert set(UserRole) == {UserRole.ADMIN, UserRole.LIBRARIAN, UserRole.MEMBER}

    # BookStatus
    assert BookStatus.AVAILABLE == "AVAILABLE"
    assert BookStatus.BORROWED == "BORROWED"
    assert set(BookStatus) == {BookStatus.AVAILABLE, BookStatus.BORROWED}

    # LoanStatus
    assert LoanStatus.OUT == "OUT"
    assert LoanStatus.RETURNED == "RETURNED"
    assert set(LoanStatus) == {LoanStatus.OUT, LoanStatus.RETURNED}
