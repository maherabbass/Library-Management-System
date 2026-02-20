import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.book import BookStatus


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    published_year: int | None = None
    description: str | None = None
    tags: list[str] | None = None


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    published_year: int | None = None
    description: str | None = None
    tags: list[str] | None = None
    status: BookStatus | None = None


class BookResponse(BaseModel):
    id: uuid.UUID
    title: str
    author: str
    isbn: str | None
    published_year: int | None
    description: str | None
    tags: list[str] | None
    status: BookStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int
