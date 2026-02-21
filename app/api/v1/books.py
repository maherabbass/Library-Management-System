import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.book import BookStatus
from app.models.user import User, UserRole
from app.schemas.ai import AISearchResponse, AskRequest, AskResponse, EnrichRequest, EnrichResponse
from app.schemas.book import BookCreate, BookListResponse, BookResponse, BookUpdate
from app.services.ai import enrich_book_metadata
from app.services.book import create_book, delete_book, get_book, list_books, update_book
from app.services.library_chat import ask_library
from app.services.semantic_search import semantic_book_search

router = APIRouter(prefix="/api/v1/books", tags=["books"])


# ---------------------------------------------------------------------------
# AI endpoints — fixed paths, registered before /{book_id} routes
# ---------------------------------------------------------------------------


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    dependencies=[require_role(UserRole.LIBRARIAN, UserRole.ADMIN)],
    summary="Option A — Generate AI metadata for a book (no DB write)",
)
async def enrich_book_endpoint(data: EnrichRequest) -> EnrichResponse:
    """
    Generate summary, tags, and keywords for a book.
    The librarian reviews and can save the output via POST /books or PUT /books/{id}.
    """
    result = await enrich_book_metadata(
        title=data.title,
        author=data.author,
        description=data.description,
    )
    return EnrichResponse(
        summary=result.summary,
        tags=result.tags,
        keywords=result.keywords,
        source=result.source,
    )


@router.get(
    "/ai-search",
    response_model=AISearchResponse,
    summary="Option B — Semantic search using embeddings (public)",
)
async def ai_search_endpoint(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    top_k: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    db: AsyncSession = Depends(get_db),
) -> AISearchResponse:
    """
    Rank books by semantic similarity to the query using OpenAI embeddings.
    Falls back to ILIKE search when OPENAI_API_KEY is not configured.
    """
    result = await semantic_book_search(db, query=q, top_k=top_k)
    return AISearchResponse(
        items=result.items,
        total=result.total,
        source=result.source,
        query=result.query,
    )


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Option C — Ask the Library assistant (authenticated users)",
)
async def ask_library_endpoint(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AskResponse:
    """
    Ask a natural language question answered using ONLY books in the database.
    The response always includes the source books for transparency.
    """
    result = await ask_library(db, question=body.question)
    return AskResponse(
        answer=result.answer,
        books=result.books,
        source=result.source,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


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
