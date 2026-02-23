import math
import uuid

from fastapi import HTTPException
from sqlalchemy import any_, delete, func, literal, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookStatus
from app.models.loan import Loan, LoanStatus
from app.schemas.book import BookCreate, BookListResponse, BookResponse, BookUpdate


async def list_books(
    db: AsyncSession,
    *,
    q: str | None = None,
    author: str | None = None,
    tag: str | None = None,
    status: BookStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> BookListResponse:
    stmt = select(Book)

    if q:
        stmt = stmt.where(
            or_(
                Book.title.ilike(f"%{q}%"),
                Book.author.ilike(f"%{q}%"),
                Book.isbn.ilike(f"%{q}%"),
                Book.description.ilike(f"%{q}%"),
            )
        )
    if author:
        stmt = stmt.where(Book.author.ilike(f"%{author}%"))
    if tag:
        stmt = stmt.where(literal(tag) == any_(Book.tags))
    if status:
        stmt = stmt.where(Book.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    data_stmt = (
        stmt.order_by(Book.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(data_stmt)).scalars().all()

    pages = math.ceil(total / page_size) if page_size else 1

    return BookListResponse(
        items=[BookResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def get_book(db: AsyncSession, book_id: uuid.UUID) -> Book:
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    book = Book(
        title=data.title,
        author=data.author,
        isbn=data.isbn,
        published_year=data.published_year,
        description=data.description,
        tags=data.tags,
    )
    db.add(book)
    try:
        await db.commit()
        await db.refresh(book)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="A book with this ISBN already exists"
        )
    return book


async def update_book(db: AsyncSession, book_id: uuid.UUID, data: BookUpdate) -> Book:
    book = await get_book(db, book_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)

    try:
        await db.commit()
        await db.refresh(book)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="A book with this ISBN already exists"
        )
    return book


async def delete_book(db: AsyncSession, book_id: uuid.UUID) -> None:
    book = await get_book(db, book_id)

    # Reject if the book is currently borrowed
    active_loan = (
        await db.execute(
            select(Loan).where(Loan.book_id == book_id, Loan.status == LoanStatus.OUT)
        )
    ).scalar_one_or_none()
    if active_loan:
        raise HTTPException(
            status_code=409, detail="Cannot delete a book that is currently borrowed"
        )

    # Remove historical loan records before deleting the book (FK is RESTRICT)
    await db.execute(delete(Loan).where(Loan.book_id == book_id))

    await db.delete(book)
    await db.commit()
