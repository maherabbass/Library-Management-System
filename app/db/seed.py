"""
Seed script — populates the database with initial data for development.

Run with:
    python -m app.db.seed
"""

import asyncio

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.book import Book, BookStatus
from app.models.user import User, UserRole

SEED_USERS = [
    {
        "email": "admin@library.local",
        "name": "Admin User",
        "role": UserRole.ADMIN,
    },
    {
        "email": "librarian@library.local",
        "name": "Jane Librarian",
        "role": UserRole.LIBRARIAN,
    },
    {
        "email": "member@library.local",
        "name": "John Member",
        "role": UserRole.MEMBER,
    },
]

SEED_BOOKS = [
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "isbn": "9780743273565",
        "published_year": 1925,
        "tags": ["fiction", "classic"],
        "description": "A story of wealth, class, love, and the American Dream in the 1920s.",
    },
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "isbn": "9780061935466",
        "published_year": 1960,
        "tags": ["fiction", "classic", "social"],
        "description": "A young girl's perspective on racial injustice in the American South.",
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "9780451524935",
        "published_year": 1949,
        "tags": ["fiction", "dystopia", "classic"],
        "description": "A totalitarian future society under constant surveillance by Big Brother.",
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "isbn": "9780441013593",
        "published_year": 1965,
        "tags": ["fiction", "sci-fi"],
        "description": "An epic saga of politics, religion, and ecology on a desert planet.",
    },
    {
        "title": "The Hitchhiker's Guide to the Galaxy",
        "author": "Douglas Adams",
        "isbn": "9780345391803",
        "published_year": 1979,
        "tags": ["fiction", "sci-fi", "comedy"],
        "description": "A hapless Earthman travels the galaxy after Earth is demolished.",
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "isbn": "9780060850524",
        "published_year": 1932,
        "tags": ["fiction", "dystopia"],
        "description": "A genetically engineered future society built on consumption and conditioning.",
    },
    {
        "title": "The Lord of the Rings",
        "author": "J.R.R. Tolkien",
        "isbn": "9780618640157",
        "published_year": 1954,
        "tags": ["fiction", "fantasy", "classic"],
        "description": "A hobbit and his companions embark on a quest to destroy a powerful ring.",
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "isbn": "9780141439518",
        "published_year": 1813,
        "tags": ["fiction", "classic", "romance"],
        "description": "Elizabeth Bennet navigates manners, morality, and marriage in Regency England.",
    },
    {
        "title": "Sapiens",
        "author": "Yuval Noah Harari",
        "isbn": "9780062316097",
        "published_year": 2011,
        "tags": ["non-fiction", "history", "science"],
        "description": "A sweeping history of humankind from the Stone Age to the present.",
    },
    {
        "title": "The Pragmatic Programmer",
        "author": "David Thomas",
        "isbn": "9780135957059",
        "published_year": 1999,
        "tags": ["tech", "programming"],
        "description": "Timeless advice for software developers on building better software.",
    },
    {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "published_year": 2008,
        "tags": ["tech", "programming"],
        "description": "A handbook of agile software craftsmanship and clean coding principles.",
    },
    {
        "title": "Design Patterns",
        "author": "Gang of Four",
        "isbn": "9780201633610",
        "published_year": 1994,
        "tags": ["tech", "programming"],
        "description": "Reusable object-oriented design solutions for common software problems.",
    },
    {
        "title": "Thinking, Fast and Slow",
        "author": "Daniel Kahneman",
        "isbn": "9780374533557",
        "published_year": 2011,
        "tags": ["non-fiction", "psychology"],
        "description": "Explores the two systems of thought that drive the way we think.",
    },
    {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "isbn": "9780062315007",
        "published_year": 1988,
        "tags": ["fiction", "philosophy"],
        "description": "A shepherd boy journeys from Spain to Egypt in pursuit of his personal legend.",
    },
    {
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "isbn": "9781451673319",
        "published_year": 1953,
        "tags": ["fiction", "dystopia", "classic"],
        "description": "A fireman tasked with burning books begins to question the society he serves.",
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Idempotency check — skip if already seeded
        user_count = await session.scalar(select(func.count()).select_from(User))
        if user_count and user_count > 0:
            print(f"Database already seeded ({user_count} users found). Skipping.")
            return

        # Create users
        users = [User(**data) for data in SEED_USERS]
        session.add_all(users)

        # Create books
        books = [Book(status=BookStatus.AVAILABLE, **data) for data in SEED_BOOKS]
        session.add_all(books)

        await session.commit()
        print(f"Seeded {len(users)} users and {len(books)} books.")


if __name__ == "__main__":
    asyncio.run(seed())
