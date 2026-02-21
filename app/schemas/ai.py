from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.book import BookResponse

# ---------------------------------------------------------------------------
# Option A — Metadata enrichment
# ---------------------------------------------------------------------------


class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    description: str | None = None


class EnrichResponse(BaseModel):
    summary: str
    tags: list[str]
    keywords: list[str]
    source: Literal["openai", "fallback"]


# ---------------------------------------------------------------------------
# Option B — Semantic search
# ---------------------------------------------------------------------------


class AISearchResponse(BaseModel):
    items: list[BookResponse]
    total: int
    source: Literal["openai", "fallback"]
    query: str


# ---------------------------------------------------------------------------
# Option C — Ask the Library
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class AskResponse(BaseModel):
    answer: str
    books: list[BookResponse]  # grounding sources from DB — always from real records
    source: Literal["openai", "fallback"]
