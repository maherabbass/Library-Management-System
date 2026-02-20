"""initial_schema

Revision ID: 6998e959
Revises:
Create Date: 2026-02-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6998e959"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Enum types ---
    userrole = postgresql.ENUM("ADMIN", "LIBRARIAN", "MEMBER", name="userrole")
    bookstatus = postgresql.ENUM("AVAILABLE", "BORROWED", name="bookstatus")
    loanstatus = postgresql.ENUM("OUT", "RETURNED", name="loanstatus")
    userrole.create(op.get_bind())
    bookstatus.create(op.get_bind())
    loanstatus.create(op.get_bind())

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "LIBRARIAN", "MEMBER", name="userrole", create_type=False),
            server_default="MEMBER",
            nullable=False,
        ),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        sa.Column("oauth_subject", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- books ---
    op.create_table(
        "books",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("published_year", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "status",
            sa.Enum("AVAILABLE", "BORROWED", name="bookstatus", create_type=False),
            server_default="AVAILABLE",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isbn"),
    )

    # --- loans ---
    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "checked_out_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("returned_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("OUT", "RETURNED", name="loanstatus", create_type=False),
            server_default="OUT",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Partial unique index — one active loan per book
    op.execute("""
        CREATE UNIQUE INDEX uq_active_loan_per_book
        ON loans (book_id)
        WHERE status = 'OUT'
        """)


def downgrade() -> None:
    op.drop_index("uq_active_loan_per_book", table_name="loans")
    op.drop_table("loans")
    op.drop_table("books")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop enum types
    sa.Enum(name="loanstatus").drop(op.get_bind())
    sa.Enum(name="bookstatus").drop(op.get_bind())
    sa.Enum(name="userrole").drop(op.get_bind())
