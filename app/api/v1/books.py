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

# Shared error response definitions
_AUTH_RESPONSES: dict = {
    401: {"description": "Missing, invalid, or expired Bearer token."},
}
_LIBRARIAN_RESPONSES: dict = {
    **_AUTH_RESPONSES,
    403: {"description": "Forbidden — Librarian or Admin role required."},
}
_NOT_FOUND_RESPONSE: dict = {
    404: {"description": "Book not found."},
}

# ---------------------------------------------------------------------------
# AI endpoints — fixed paths, registered before /{book_id} routes
# ---------------------------------------------------------------------------


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    dependencies=[require_role(UserRole.LIBRARIAN, UserRole.ADMIN)],
    tags=["ai"],
    summary="Generate AI metadata (no DB write)",
    description=(
        "Generates a **summary**, **tags**, and **keywords** for a book using OpenAI.\n\n"
        "This endpoint is **preview-only** — nothing is written to the database. "
        "The librarian reviews the output and then includes it when calling "
        "`POST /books` (create) or `PUT /books/{id}` (update).\n\n"
        "**Fallback:** if `OPENAI_API_KEY` is not set or the AI call fails, a "
        "deterministic heuristic is used instead. Check `source` in the response.\n\n"
        "**Requires:** Librarian or Admin role."
    ),
    response_description="Generated metadata — summary, tags, keywords, and the source that produced them.",
    responses={
        **_LIBRARIAN_RESPONSES,
        422: {"description": "Validation error — `title` and `author` are required."},
    },
)
async def enrich_book_endpoint(data: EnrichRequest) -> EnrichResponse:
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
    tags=["ai"],
    summary="Semantic search with embeddings",
    description=(
        "Ranks books by **semantic similarity** to a natural-language query using "
        "OpenAI text embeddings and cosine similarity.\n\n"
        "This endpoint is **public** — no authentication required.\n\n"
        "**Fallback:** when `OPENAI_API_KEY` is not configured, a standard "
        "ILIKE keyword search is performed instead. The `source` field indicates "
        "which method was used.\n\n"
        "**Example queries:**\n"
        "- `books about dystopian futures`\n"
        "- `science fiction with strong female protagonists`\n"
        "- `classic literature set in 19th century England`"
    ),
    response_description="Ranked list of matching books with search metadata.",
)
async def ai_search_endpoint(
    q: str = Query(
        ...,
        min_length=1,
        description="Natural-language search query.",
        examples=["books about space exploration"],
    ),
    top_k: int = Query(10, ge=1, le=50, description="Maximum number of results to return (1–50)."),
    db: AsyncSession = Depends(get_db),
) -> AISearchResponse:
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
    tags=["ai"],
    summary="Ask the Library assistant",
    description=(
        "Ask a natural-language question and receive an answer grounded **exclusively** "
        "in books that exist in the database.\n\n"
        "The assistant never invents titles, authors, or availability — every claim is "
        "backed by a real database record returned in the `books` array.\n\n"
        "**Fallback:** when `OPENAI_API_KEY` is not configured, a pre-built template "
        "answer is returned using the matched books.\n\n"
        "**Example questions:**\n"
        "- `Do you have any books by Isaac Asimov?`\n"
        "- `What science fiction books are available?`\n"
        "- `Can you recommend something about machine learning?`\n\n"
        "**Requires:** any authenticated user (Member, Librarian, or Admin)."
    ),
    response_description="Grounded answer with the database records that support it.",
    responses={
        **_AUTH_RESPONSES,
        422: {
            "description": "Validation error — `question` is required and must be ≤500 characters."
        },
    },
)
async def ask_library_endpoint(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AskResponse:
    result = await ask_library(db, question=body.question)
    return AskResponse(
        answer=result.answer,
        books=result.books,
        source=result.source,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=BookListResponse,
    summary="List books",
    description=(
        "Returns a **paginated, filterable** list of books from the catalogue.\n\n"
        "This endpoint is **public** — no authentication required.\n\n"
        "**Filters (all optional, combinable):**\n\n"
        "| Parameter | Behaviour |\n"
        "|-----------|----------|\n"
        "| `q` | Case-insensitive substring match across title, author, ISBN, and description |\n"
        "| `author` | Case-insensitive substring match on the author field only |\n"
        "| `tag` | Exact match against the tags array |\n"
        "| `status` | `AVAILABLE` or `BORROWED` |\n\n"
        "Results are ordered by `created_at` descending (newest first)."
    ),
    response_description="Paginated book list with total count and page metadata.",
)
async def list_books_endpoint(
    q: str | None = Query(
        None,
        description="Free-text search across title, author, ISBN, and description (case-insensitive).",
        examples=["Frank Herbert"],
    ),
    author: str | None = Query(
        None,
        description="Filter by author name (case-insensitive substring match).",
        examples=["Tolkien"],
    ),
    tag: str | None = Query(
        None,
        description="Filter by exact tag value.",
        examples=["science-fiction"],
    ),
    status: BookStatus | None = Query(
        None,
        description="Filter by availability status: `AVAILABLE` or `BORROWED`.",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page (1–100)."),
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
    summary="Create a book",
    description=(
        "Adds a new book to the catalogue.\n\n"
        "The book is created with status `AVAILABLE`. "
        "Only `title` and `author` are required — all other fields are optional.\n\n"
        "**Tip:** call `POST /books/enrich` first to generate AI-suggested tags and "
        "description, then include them in this request.\n\n"
        "**Requires:** Librarian or Admin role."
    ),
    response_description="The newly created book record.",
    responses={
        **_LIBRARIAN_RESPONSES,
        409: {"description": "A book with the same ISBN already exists."},
        422: {"description": "Validation error — check `title` and `author` are non-empty."},
    },
)
async def create_book_endpoint(
    data: BookCreate,
    db: AsyncSession = Depends(get_db),
) -> BookResponse:
    book = await create_book(db, data)
    return BookResponse.model_validate(book)


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    summary="Get a book",
    description=(
        "Returns the full details of a single book by its UUID.\n\n"
        "This endpoint is **public** — no authentication required."
    ),
    response_description="The requested book record.",
    responses={
        **_NOT_FOUND_RESPONSE,
    },
)
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
    summary="Update a book",
    description=(
        "Partially updates a book's metadata using the provided fields.\n\n"
        "Only fields included in the request body are changed — omitted fields keep "
        "their current values (partial update / PATCH semantics on a PUT).\n\n"
        "**Requires:** Librarian or Admin role."
    ),
    response_description="The updated book record.",
    responses={
        **_LIBRARIAN_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        422: {"description": "Validation error — check field types and constraints."},
    },
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
    summary="Delete a book",
    description=(
        "Permanently removes a book from the catalogue.\n\n"
        "> **Warning:** this operation is irreversible. Associated loan history is "
        "also deleted via cascade.\n\n"
        "**Requires:** Librarian or Admin role."
    ),
    response_description="No content — the book was successfully deleted.",
    responses={
        **_LIBRARIAN_RESPONSES,
        **_NOT_FOUND_RESPONSE,
    },
)
async def delete_book_endpoint(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_book(db, book_id)
