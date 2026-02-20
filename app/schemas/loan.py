import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.loan import LoanStatus


class CheckoutRequest(BaseModel):
    book_id: uuid.UUID


class ReturnRequest(BaseModel):
    loan_id: uuid.UUID


class LoanResponse(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: uuid.UUID
    checked_out_at: datetime
    returned_at: datetime | None
    status: LoanStatus

    model_config = ConfigDict(from_attributes=True)


class LoanListResponse(BaseModel):
    items: list[LoanResponse]
    total: int
