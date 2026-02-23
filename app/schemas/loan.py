import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.loan import LoanStatus

_EXAMPLE_BOOK_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
_EXAMPLE_LOAN_ID = "8a1bc234-9876-4def-b3fc-1a2b3c4d5e6f"
_EXAMPLE_USER_ID = "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"


class CheckoutRequest(BaseModel):
    book_id: uuid.UUID = Field(
        ...,
        description="UUID of the book to borrow. The book must have status `AVAILABLE`.",
        examples=[_EXAMPLE_BOOK_ID],
    )

    model_config = ConfigDict(json_schema_extra={"example": {"book_id": _EXAMPLE_BOOK_ID}})


class ReturnRequest(BaseModel):
    loan_id: uuid.UUID = Field(
        ...,
        description=(
            "UUID of the active loan to close. "
            "Members may only supply their **own** loan IDs. "
            "Librarians and Admins may supply any loan ID."
        ),
        examples=[_EXAMPLE_LOAN_ID],
    )

    model_config = ConfigDict(json_schema_extra={"example": {"loan_id": _EXAMPLE_LOAN_ID}})


class LoanResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Unique loan identifier (UUID v4).")
    book_id: uuid.UUID = Field(..., description="UUID of the borrowed book.")
    user_id: uuid.UUID = Field(..., description="UUID of the user who borrowed the book.")
    checked_out_at: datetime = Field(
        ..., description="UTC timestamp when the book was checked out."
    )
    returned_at: datetime | None = Field(
        None,
        description="UTC timestamp when the book was returned. `null` if still checked out.",
    )
    status: LoanStatus = Field(
        ...,
        description="Loan status: `OUT` — book is still borrowed; `RETURNED` — book has been returned.",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_LOAN_ID,
                "book_id": _EXAMPLE_BOOK_ID,
                "user_id": _EXAMPLE_USER_ID,
                "checked_out_at": "2024-01-20T09:00:00Z",
                "returned_at": None,
                "status": "OUT",
            }
        },
    )


class LoanListResponse(BaseModel):
    items: list[LoanResponse] = Field(..., description="Loans on the current page.")
    total: int = Field(..., description="Total number of loans matching the current query.")

    model_config = ConfigDict(json_schema_extra={"example": {"items": [], "total": 0}})
