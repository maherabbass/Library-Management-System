"""Option B — Semantic search using OpenAI embeddings.

Embeds the query and every book's text in one batch API call, ranks by
cosine similarity, and returns the top-k results.

Falls back to basic ILIKE search (same as GET /books?q=...) when
OPENAI_API_KEY is not configured or any provider error occurs.
"""

import logging
import math
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import Book
from app.schemas.book import BookResponse
from app.services.book import list_books

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure-Python vector math — no extra dependencies
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity in [-1, 1]. Returns 0.0 for zero vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Book → text representation used for embedding
# ---------------------------------------------------------------------------


def _book_text(book: Book) -> str:
    """Combine title, author, description and tags into a single embedding text."""
    parts = [f"{book.title} by {book.author}"]
    if book.description:
        parts.append(book.description)
    if book.tags:
        parts.append(" ".join(book.tags))
    return ". ".join(parts)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class SemanticSearchResult:
    items: list[BookResponse] = field(default_factory=list)
    total: int = 0
    source: str = "fallback"  # "openai" | "fallback"
    query: str = ""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def semantic_book_search(
    db: AsyncSession,
    *,
    query: str,
    top_k: int = 10,
) -> SemanticSearchResult:
    """
    Search books by semantic similarity to *query*.

    With OpenAI configured:
      - Batch-embed all books + the query in one API call.
      - Rank books by cosine similarity to the query vector.
      - Return top_k results.

    Without OpenAI (or on any provider error):
      - Fall back to basic ILIKE search (GET /books?q=...).
    """
    if not settings.OPENAI_API_KEY or settings.AI_PROVIDER != "openai":
        return await _fallback_search(db, query=query, top_k=top_k)

    try:
        return await _openai_search(db, query=query, top_k=top_k)
    except Exception as exc:
        logger.warning("Semantic search failed (%s), using fallback", type(exc).__name__)
        return await _fallback_search(db, query=query, top_k=top_k)


# ---------------------------------------------------------------------------
# Fallback — ILIKE (reuses Phase 2 logic)
# ---------------------------------------------------------------------------


async def _fallback_search(db: AsyncSession, *, query: str, top_k: int) -> SemanticSearchResult:
    result = await list_books(db, q=query, page=1, page_size=top_k)
    return SemanticSearchResult(
        items=result.items,
        total=result.total,
        source="fallback",
        query=query,
    )


# ---------------------------------------------------------------------------
# OpenAI embedding path
# ---------------------------------------------------------------------------


async def _openai_search(db: AsyncSession, *, query: str, top_k: int) -> SemanticSearchResult:
    # Load all books; small libraries fit comfortably in memory
    all_books: list[Book] = list((await db.scalars(select(Book))).all())
    if not all_books:
        return SemanticSearchResult(items=[], total=0, source="openai", query=query)

    # Build one input list: [book_0_text, ..., book_n_text, query]
    book_texts = [_book_text(b) for b in all_books]
    inputs = book_texts + [query]

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=inputs,
    )

    # OpenAI returns embeddings in the same order as *input*
    all_embeddings = [e.embedding for e in response.data]
    query_vec = all_embeddings[-1]
    book_vecs = all_embeddings[:-1]

    # Score and sort descending
    scored = sorted(
        zip(all_books, book_vecs),
        key=lambda pair: _cosine_similarity(query_vec, pair[1]),
        reverse=True,
    )

    top_books = [b for b, _ in scored[:top_k]]
    return SemanticSearchResult(
        items=[BookResponse.model_validate(b) for b in top_books],
        total=len(all_books),
        source="openai",
        query=query,
    )
