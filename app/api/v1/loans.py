from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.loan import CheckoutRequest, LoanListResponse, LoanResponse, ReturnRequest
from app.services.loan import checkout_book, list_loans, return_book

router = APIRouter(prefix="/api/v1/loans", tags=["loans"])


@router.post("/checkout", response_model=LoanResponse, status_code=201)
async def checkout_endpoint(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanResponse:
    loan = await checkout_book(db, book_id=body.book_id, current_user=current_user)
    return LoanResponse.model_validate(loan)


@router.post("/return", response_model=LoanResponse)
async def return_endpoint(
    body: ReturnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanResponse:
    loan = await return_book(db, loan_id=body.loan_id, current_user=current_user)
    return LoanResponse.model_validate(loan)


@router.get("", response_model=LoanListResponse)
async def list_loans_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanListResponse:
    loans, total = await list_loans(db, current_user=current_user, page=page, page_size=page_size)
    return LoanListResponse(
        items=[LoanResponse.model_validate(loan) for loan in loans],
        total=total,
    )
