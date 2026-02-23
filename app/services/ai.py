"""AI metadata enrichment service.

Tries OpenAI when OPENAI_API_KEY is configured.
Falls back to deterministic heuristics on any failure or missing key.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Words too generic to be useful as tags / keywords
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "its",
        "this",
        "that",
    }
)


@dataclass
class EnrichmentResult:
    summary: str
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    source: str = "fallback"  # "openai" | "fallback"


# ---------------------------------------------------------------------------
# Fallback — pure heuristics, fully deterministic
# ---------------------------------------------------------------------------


def _extract_words(text: str, min_len: int = 3) -> list[str]:
    """Return unique lowercase words of at least *min_len* chars, stopwords removed, order-preserved."""
    raw = re.findall(r"\b[a-zA-Z]{%d,}\b" % min_len, text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for w in raw:
        if w not in _STOPWORDS and w not in seen:
            seen.add(w)
            result.append(w)
    return result


def _fallback_enrich(title: str, author: str, description: str | None) -> EnrichmentResult:
    # Summary: use description if provided, else compose a generic one
    if description and description.strip():
        summary = description.strip()
        if not summary.endswith((".", "!", "?")):
            summary += "."
    else:
        summary = f"A book by {author} titled '{title}'."

    # Tags: unique words from title + author combined (up to 5)
    tags = _extract_words(f"{title} {author}")[:5]

    # Keywords: words from title, then append author's last name if new (up to 7)
    keywords = _extract_words(title)[:6]
    author_parts = author.strip().split()
    if author_parts:
        last = author_parts[-1].lower()
        if last not in _STOPWORDS and last not in keywords and len(last) >= 3:
            keywords.append(last)
    keywords = keywords[:7]

    return EnrichmentResult(summary=summary, tags=tags, keywords=keywords, source="fallback")


# ---------------------------------------------------------------------------
# OpenAI enrichment
# ---------------------------------------------------------------------------


async def _openai_enrich(title: str, author: str, description: str | None) -> EnrichmentResult:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    desc_part = f"\nDescription: {description}" if description else ""
    user_content = (
        f"Generate library metadata for this book.\n"
        f"Title: {title}\n"
        f"Author: {author}{desc_part}\n\n"
        'Return JSON with exactly these keys: "summary" (string, 1-2 sentences), '
        '"tags" (array of 3-5 lowercase strings), '
        '"keywords" (array of 5-8 search-term strings).'
    )

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a library metadata specialist. "
                    "Generate accurate, concise metadata. "
                    "Respond with valid JSON only."
                ),
            },
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=300,
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

    return EnrichmentResult(
        summary=str(data.get("summary", f"A book by {author} titled '{title}'.")),
        tags=[str(t) for t in data.get("tags", [])],
        keywords=[str(k) for k in data.get("keywords", [])],
        source="openai",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _is_ai_configured() -> bool:
    return bool(settings.OPENAI_API_KEY and settings.AI_PROVIDER == "openai")


async def enrich_book_metadata(
    title: str,
    author: str,
    description: str | None = None,
) -> EnrichmentResult:
    """
    Return enrichment metadata for a book.

    Uses OpenAI when configured; falls back to deterministic heuristics
    on missing key or any provider error.
    """
    if not _is_ai_configured():
        return _fallback_enrich(title, author, description)

    try:
        return await _openai_enrich(title, author, description)
    except Exception as exc:
        logger.warning("AI enrichment failed (%s: %s), using fallback", type(exc).__name__, exc)
        return _fallback_enrich(title, author, description)
