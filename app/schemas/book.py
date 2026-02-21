import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.book import BookStatus

_DUNE_EXAMPLE = {
    "title": "Dune",
    "author": "Frank Herbert",
    "isbn": "978-0441013593",
    "published_year": 1965,
    "description": "A science fiction epic set on the desert planet Arrakis.",
    "tags": ["science-fiction", "epic", "classic"],
}


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title.", examples=["Dune"])
    author: str = Field(
        ...,
        min_length=1,
        description="Full name of the primary author.",
        examples=["Frank Herbert"],
    )
    isbn: str | None = Field(
        None,
        description="ISBN-10 or ISBN-13. Must be unique across all books if provided.",
        examples=["978-0441013593"],
    )
    published_year: int | None = Field(
        None,
        ge=1000,
        le=2100,
        description="Year the book was first published.",
        examples=[1965],
    )
    description: str | None = Field(
        None,
        description="Short synopsis or notes about the book.",
        examples=["A science fiction epic set on the desert planet Arrakis."],
    )
    tags: list[str] | None = Field(
        None,
        description="Free-form classification tags (e.g. genre, topic).",
        examples=[["science-fiction", "epic", "classic"]],
    )

    model_config = ConfigDict(json_schema_extra={"example": _DUNE_EXAMPLE})


class BookUpdate(BaseModel):
    title: str | None = Field(None, description="New title. Omit to keep the current value.")
    author: str | None = Field(None, description="New author. Omit to keep the current value.")
    isbn: str | None = Field(None, description="New ISBN. Omit to keep the current value.")
    published_year: int | None = Field(
        None, description="New publication year. Omit to keep the current value."
    )
    description: str | None = Field(
        None, description="New description. Omit to keep the current value."
    )
    tags: list[str] | None = Field(
        None,
        description="Replaces the **entire** tag list. Send an empty list `[]` to clear tags.",
    )
    status: BookStatus | None = Field(
        None,
        description=(
            "Override the book status. "
            "Normally managed automatically by checkout/return — use with care."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Updated synopsis of the Dune novel.",
                "tags": ["science-fiction", "epic", "desert"],
            }
        }
    )


class BookResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Unique book identifier (UUID v4).")
    title: str = Field(..., description="Book title.")
    author: str = Field(..., description="Primary author.")
    isbn: str | None = Field(None, description="ISBN-10 or ISBN-13, if provided.")
    published_year: int | None = Field(None, description="Year first published.")
    description: str | None = Field(None, description="Synopsis or notes.")
    tags: list[str] | None = Field(None, description="Classification tags.")
    status: BookStatus = Field(
        ...,
        description="Current availability: `AVAILABLE` — can be borrowed; `BORROWED` — checked out.",
    )
    created_at: datetime = Field(..., description="Timestamp when the record was created (UTC).")
    updated_at: datetime = Field(..., description="Timestamp of the last update (UTC).")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                **_DUNE_EXAMPLE,
                "status": "AVAILABLE",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    )


class BookListResponse(BaseModel):
    items: list[BookResponse] = Field(..., description="Books on the current page.")
    total: int = Field(..., description="Total number of books matching the current filters.")
    page: int = Field(..., description="Current page number (1-based).")
    page_size: int = Field(..., description="Maximum items returned per page.")
    pages: int = Field(..., description="Total number of pages.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 42,
                "page": 1,
                "page_size": 20,
                "pages": 3,
            }
        }
    )
