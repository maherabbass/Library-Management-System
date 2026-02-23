"""Option C — "Ask the Library" grounded chat assistant.

Always retrieves relevant books from the DB first, then crafts a
constrained prompt that prevents the model from inventing books.

Falls back to a formatted catalog excerpt (no LLM) when OPENAI_API_KEY
is missing or any provider error occurs.
"""

import logging
import re
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import Book, BookStatus
from app.schemas.book import BookResponse

logger = logging.getLogger(__name__)

_MAX_CONTEXT_BOOKS = 20  # cap the catalog context sent to the model

# Words too common to be useful as library search terms
_CHAT_STOPWORDS = frozenset(
    {
        "what",
        "which",
        "where",
        "when",
        "who",
        "how",
        "can",
        "you",
        "are",
        "the",
        "and",
        "have",
        "has",
        "for",
        "that",
        "with",
        "your",
        "this",
        "those",
        "tell",
        "list",
        "show",
        "give",
        "find",
        "about",
        "any",
        "all",
        "book",
        "books",
        "look",
        "like",
        "want",
        "need",
        "does",
        "did",
        "was",
        "were",
        "its",
        "from",
        "not",
        "but",
        "into",
    }
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ChatResult:
    answer: str
    books: list[BookResponse] = field(default_factory=list)
    source: str = "fallback"  # "openai" | "fallback"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def ask_library(db: AsyncSession, *, question: str) -> ChatResult:
    """
    Answer a library question grounded in the actual DB catalog.

    Retrieval always happens from the DB first — the model only sees books
    that exist in the database, preventing hallucinated records.
    """
    books = await _retrieve_relevant_books(db, question=question)

    if not settings.OPENAI_API_KEY or settings.AI_PROVIDER != "openai":
        return _fallback_answer(question=question, books=books)

    try:
        return await _openai_answer(question=question, books=books)
    except Exception as exc:
        logger.warning("Library chat failed (%s), using fallback", type(exc).__name__)
        return _fallback_answer(question=question, books=books)


# ---------------------------------------------------------------------------
# Retrieval — always from DB
# ---------------------------------------------------------------------------


async def _retrieve_relevant_books(db: AsyncSession, *, question: str) -> list[Book]:
    """Extract meaningful keywords from the question and ILIKE-search the catalog."""
    raw_words = re.findall(r"\b[a-zA-Z]{3,}\b", question.lower())
    keywords = [w for w in dict.fromkeys(raw_words) if w not in _CHAT_STOPWORDS]

    if not keywords:
        # Nothing useful extracted → return the most recently added books as context
        rows = await db.scalars(
            select(Book).order_by(Book.created_at.desc()).limit(_MAX_CONTEXT_BOOKS)
        )
        return list(rows.all())

    conditions = []
    for kw in keywords:
        like = f"%{kw}%"
        conditions.extend(
            [
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.description.ilike(like),
            ]
        )

    rows = await db.scalars(
        select(Book)
        .where(or_(*conditions))
        .order_by(Book.created_at.desc())
        .limit(_MAX_CONTEXT_BOOKS)
    )
    return list(rows.all())


# ---------------------------------------------------------------------------
# Fallback — deterministic, no LLM
# ---------------------------------------------------------------------------


def _build_catalog_context(books: list[Book]) -> str:
    """Format a numbered catalog list from ORM Book objects."""
    if not books:
        return "No relevant books found in the catalog."
    lines = []
    for i, b in enumerate(books, 1):
        status_label = "Available" if b.status == BookStatus.AVAILABLE else "Borrowed"
        desc_part = f" — {b.description[:100]}" if b.description else ""
        tags_part = f" [tags: {', '.join(b.tags)}]" if b.tags else ""
        lines.append(
            f'{i}. "{b.title}" by {b.author}'
            f" ({b.published_year or 'n/a'}) [{status_label}]{desc_part}{tags_part}"
        )
    return "\n".join(lines)


def _fallback_answer(*, question: str, books: list[Book]) -> ChatResult:
    book_responses = [BookResponse.model_validate(b) for b in books]
    if not books:
        answer = (
            "I couldn't find any books in our catalog relevant to your question. "
            "Try browsing the full catalog at GET /api/v1/books."
        )
    else:
        header = "Based on our library catalog, here are the most relevant results:"
        lines = [header]
        for i, b in enumerate(books[:10], 1):
            status_label = "Available" if b.status == BookStatus.AVAILABLE else "Currently borrowed"
            desc_part = f" — {b.description[:80]}..." if b.description else ""
            lines.append(f'{i}. "{b.title}" by {b.author} [{status_label}]{desc_part}')
        answer = "\n".join(lines)
    return ChatResult(answer=answer, books=book_responses, source="fallback")


# ---------------------------------------------------------------------------
# OpenAI grounded answer
# ---------------------------------------------------------------------------


async def _openai_answer(*, question: str, books: list[Book]) -> ChatResult:
    catalog_context = _build_catalog_context(books)
    book_responses = [BookResponse.model_validate(b) for b in books]

    system_prompt = (
        "You are a helpful library assistant. "
        "You MUST answer using ONLY the books listed in the catalog below. "
        "Do NOT mention, recommend, or reference any book not in this list. "
        "If the question cannot be answered from the catalog, say so clearly. "
        "Be concise and friendly.\n\n"
        f"Library Catalog (relevant results):\n{catalog_context}"
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
        max_tokens=500,
    )

    answer = (response.choices[0].message.content or "").strip()
    return ChatResult(answer=answer, books=book_responses, source="openai")
