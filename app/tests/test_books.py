import uuid

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas.book import BookCreate, BookUpdate

# ---------------------------------------------------------------------------
# Schema-only tests (no DB required)
# ---------------------------------------------------------------------------


def test_book_schema_validation_missing_title() -> None:
    with pytest.raises(ValidationError):
        BookCreate(author="Someone")  # type: ignore[call-arg]


def test_book_schema_validation_missing_author() -> None:
    with pytest.raises(ValidationError):
        BookCreate(title="Some Title")  # type: ignore[call-arg]


def test_book_update_all_optional() -> None:
    # BookUpdate should accept an empty payload (all fields optional)
    update = BookUpdate()
    assert update.title is None
    assert update.author is None
    assert update.status is None


# ---------------------------------------------------------------------------
# DB-dependent tests (skip if Postgres is unavailable)
# ---------------------------------------------------------------------------

BOOK_PAYLOAD = {
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "isbn": "978-0743273565",
    "published_year": 1925,
    "description": "A classic American novel",
    "tags": ["fiction", "classic"],
}


async def test_create_book(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/books", json=BOOK_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == BOOK_PAYLOAD["title"]
    assert data["author"] == BOOK_PAYLOAD["author"]
    assert data["isbn"] == BOOK_PAYLOAD["isbn"]
    assert data["published_year"] == BOOK_PAYLOAD["published_year"]
    assert data["tags"] == BOOK_PAYLOAD["tags"]
    assert data["status"] == "AVAILABLE"
    assert "id" in data


async def test_create_book_duplicate_isbn(client: AsyncClient) -> None:
    payload = {**BOOK_PAYLOAD, "isbn": f"dup-{uuid.uuid4().hex[:8]}"}
    resp1 = await client.post("/api/v1/books", json=payload)
    assert resp1.status_code == 201
    resp2 = await client.post("/api/v1/books", json=payload)
    assert resp2.status_code == 409


async def test_get_book(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/books", json={**BOOK_PAYLOAD, "isbn": None})
    assert create_resp.status_code == 201
    book_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
    assert data["title"] == BOOK_PAYLOAD["title"]


async def test_get_book_not_found(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/books/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_list_books(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/books")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data


async def test_search_books(client: AsyncClient) -> None:
    # Ensure Gatsby is present
    await client.post("/api/v1/books", json={**BOOK_PAYLOAD, "isbn": None})

    resp = await client.get("/api/v1/books?q=Gatsby")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any("Gatsby" in item["title"] for item in items)


async def test_filter_by_author(client: AsyncClient) -> None:
    orwell_payload = {
        "title": "1984",
        "author": "George Orwell",
        "isbn": None,
        "tags": ["fiction", "dystopian"],
    }
    await client.post("/api/v1/books", json=orwell_payload)

    resp = await client.get("/api/v1/books?author=Orwell")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert all("Orwell" in item["author"] for item in items)


async def test_filter_by_tag(client: AsyncClient) -> None:
    tagged_payload = {
        "title": "Tagged Book",
        "author": "Tag Author",
        "isbn": None,
        "tags": ["unique-tag-xyz"],
    }
    await client.post("/api/v1/books", json=tagged_payload)

    resp = await client.get("/api/v1/books?tag=unique-tag-xyz")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert all("unique-tag-xyz" in (item["tags"] or []) for item in items)


async def test_filter_by_status(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/books?status=AVAILABLE")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["status"] == "AVAILABLE" for item in items)


async def test_update_book(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/books",
        json={"title": "Original Title", "author": "Original Author", "isbn": None},
    )
    assert create_resp.status_code == 201
    book_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/books/{book_id}",
        json={"title": "Updated Title"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Title"
    # author unchanged
    assert update_resp.json()["author"] == "Original Author"

    verify_resp = await client.get(f"/api/v1/books/{book_id}")
    assert verify_resp.json()["title"] == "Updated Title"


async def test_delete_book(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/books",
        json={"title": "To Be Deleted", "author": "Delete Author", "isbn": None},
    )
    assert create_resp.status_code == 201
    book_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/books/{book_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/books/{book_id}")
    assert get_resp.status_code == 404


async def test_pagination(client: AsyncClient) -> None:
    # Create 3 fresh books with unique ISBNs to ensure they exist
    for i in range(3):
        await client.post(
            "/api/v1/books",
            json={
                "title": f"Pagination Book {uuid.uuid4().hex[:6]}",
                "author": "Pagination Author",
                "isbn": None,
            },
        )

    resp = await client.get("/api/v1/books?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3
    assert data["page"] == 1
    assert data["page_size"] == 2
