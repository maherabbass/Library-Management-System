import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.db.session import get_db
from app.models.book import BookStatus
from app.models.user import UserRole
from app.schemas.book import BookCreate, BookListResponse, BookResponse, BookUpdate
from app.services.book import create_book, delete_book, get_book, list_books, update_book

router = APIRouter(prefix="/api/v1/books", tags=["books"])


@router.get("", response_model=BookListResponse)
async def list_books_endpoint(
    q: str | None = Query(
        None, description="Free-text search across title/author/isbn/description"
    ),
    author: str | None = Query(None, description="Filter by author (ILIKE)"),
    tag: str | None = Query(None, description="Filter by tag (exact match)"),
    status: BookStatus | None = Query(None, description="Filter by book status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> BookListResponse:
    return await list_books(
        db, q=q, author=author, tag=tag, status=status, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=BookResponse,
    status_code=201,
    dependencies=[require_role(UserRole.LIBRARIAN, UserRole.ADMIN)],
)
async def create_book_endpoint(
    data: BookCreate,
    db: AsyncSession = Depends(get_db),
) -> BookResponse:
    book = await create_book(db, data)
    return BookResponse.model_validate(book)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book_endpoint(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BookResponse:
    book = await get_book(db, book_id)
    return BookResponse.model_validate(book)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[require_role(UserRole.LIBRARIAN, UserRole.ADMIN)],
)
async def update_book_endpoint(
    book_id: uuid.UUID,
    data: BookUpdate,
    db: AsyncSession = Depends(get_db),
) -> BookResponse:
    book = await update_book(db, book_id, data)
    return BookResponse.model_validate(book)


@router.delete(
    "/{book_id}",
    status_code=204,
    dependencies=[require_role(UserRole.LIBRARIAN, UserRole.ADMIN)],
)
async def delete_book_endpoint(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_book(db, book_id)
