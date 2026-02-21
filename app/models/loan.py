import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoanStatus(str, enum.Enum):
    OUT = "OUT"
    RETURNED = "RETURNED"


class Loan(Base):
    __tablename__ = "loans"

    __table_args__ = (
        Index(
            "uq_active_loan_per_book",
            "book_id",
            unique=True,
            postgresql_where=text("status = 'OUT'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checked_out_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    returned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[LoanStatus] = mapped_column(
        SAEnum(LoanStatus, name="loanstatus"),
        nullable=False,
        server_default=text("'OUT'"),
    )

    def __repr__(self) -> str:
        return f"<Loan id={self.id} book_id={self.book_id} status={self.status}>"
