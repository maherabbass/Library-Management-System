import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookStatus
from app.models.loan import Loan, LoanStatus
from app.models.user import User, UserRole


async def checkout_book(db: AsyncSession, *, book_id: uuid.UUID, current_user: User) -> Loan:
    """
    Checkout a book for the current user.

    Uses SELECT … FOR UPDATE to lock the book row so concurrent checkout
    requests serialize correctly.  The partial unique index on loans
    (WHERE status = 'OUT') is the database-level safety net.
    """
    # Lock the book row for the duration of this transaction
    book = await db.scalar(select(Book).where(Book.id == book_id).with_for_update())
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.status == BookStatus.BORROWED:
        raise HTTPException(status_code=409, detail="Book is already borrowed")

    loan = Loan(book_id=book_id, user_id=current_user.id)
    db.add(loan)
    book.status = BookStatus.BORROWED

    try:
        await db.commit()
    except IntegrityError:
        # Two concurrent requests both passed the status check;
        # the unique index caught the second one.
        await db.rollback()
        raise HTTPException(status_code=409, detail="Book is already borrowed")

    await db.refresh(loan)
    return loan


async def return_book(db: AsyncSession, *, loan_id: uuid.UUID, current_user: User) -> Loan:
    """
    Return a book.

    - MEMBER can only return their own active loan.
    - LIBRARIAN / ADMIN can return any active loan.
    """
    loan = await db.scalar(select(Loan).where(Loan.id == loan_id, Loan.status == LoanStatus.OUT))
    if loan is None:
        raise HTTPException(status_code=404, detail="Active loan not found")

    if current_user.role == UserRole.MEMBER and loan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot return another user's loan")

    loan.status = LoanStatus.RETURNED
    loan.returned_at = datetime.now(tz=timezone.utc)

    book = await db.get(Book, loan.book_id)
    if book is not None:
        book.status = BookStatus.AVAILABLE

    await db.commit()
    await db.refresh(loan)
    return loan


async def list_loans(
    db: AsyncSession,
    *,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Loan], int]:
    """
    List loans.

    - MEMBER sees only their own loans.
    - LIBRARIAN / ADMIN sees all loans.
    """
    base = select(Loan)
    if current_user.role == UserRole.MEMBER:
        base = base.where(Loan.user_id == current_user.id)

    total: int = (await db.scalar(select(func.count()).select_from(base.subquery()))) or 0

    rows = await db.scalars(
        base.order_by(Loan.checked_out_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows.all()), total
