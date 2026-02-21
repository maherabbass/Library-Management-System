from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.loan import CheckoutRequest, LoanListResponse, LoanResponse, ReturnRequest
from app.services.loan import checkout_book, list_loans, return_book

router = APIRouter(prefix="/api/v1/loans", tags=["loans"])

_AUTH_RESPONSES: dict = {
    401: {"description": "Missing, invalid, or expired Bearer token."},
}


@router.post(
    "/checkout",
    response_model=LoanResponse,
    status_code=201,
    summary="Borrow a book",
    description=(
        "Creates a new loan and marks the book as `BORROWED`.\n\n"
        "**Business rules:**\n"
        "- The book must currently have status `AVAILABLE`. If it is already `BORROWED`, "
        "the request fails with `409 Conflict`.\n"
        "- There is no limit on how many books a single user can borrow simultaneously.\n"
        "- Any authenticated user (Member, Librarian, or Admin) can borrow a book.\n\n"
        "**Concurrency:** the endpoint uses `SELECT ... FOR UPDATE` to prevent two users "
        "from borrowing the same book simultaneously.\n\n"
        "**Requires:** any authenticated user."
    ),
    response_description="The new loan record with status `OUT`.",
    responses={
        **_AUTH_RESPONSES,
        404: {"description": "Book not found."},
        409: {"description": "Conflict — the book is already borrowed by another user."},
        422: {"description": "Validation error — `book_id` must be a valid UUID."},
    },
)
async def checkout_endpoint(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanResponse:
    loan = await checkout_book(db, book_id=body.book_id, current_user=current_user)
    return LoanResponse.model_validate(loan)


@router.post(
    "/return",
    response_model=LoanResponse,
    summary="Return a book",
    description=(
        "Closes an active loan and marks the book as `AVAILABLE` again.\n\n"
        "**Business rules:**\n"
        "- The loan must have status `OUT`. Already-returned loans return `404`.\n"
        "- **Members** may only return their **own** loans — supplying another user's "
        "loan ID returns `403 Forbidden`.\n"
        "- **Librarians** and **Admins** may return any loan.\n\n"
        "**Requires:** any authenticated user."
    ),
    response_description="The closed loan record with status `RETURNED` and `returned_at` timestamp.",
    responses={
        **_AUTH_RESPONSES,
        403: {"description": "Forbidden — Members may only return their own loans."},
        404: {"description": "Loan not found or already returned."},
        422: {"description": "Validation error — `loan_id` must be a valid UUID."},
    },
)
async def return_endpoint(
    body: ReturnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanResponse:
    loan = await return_book(db, loan_id=body.loan_id, current_user=current_user)
    return LoanResponse.model_validate(loan)


@router.get(
    "",
    response_model=LoanListResponse,
    summary="List loans",
    description=(
        "Returns a paginated list of loans.\n\n"
        "**Role-based filtering:**\n"
        "- **Members** see only their **own** loans.\n"
        "- **Librarians** and **Admins** see **all** loans across all users.\n\n"
        "Results are ordered by `checked_out_at` descending (most recent first).\n\n"
        "**Requires:** any authenticated user."
    ),
    response_description="Paginated loan list.",
    responses={
        **_AUTH_RESPONSES,
    },
)
async def list_loans_endpoint(
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1–100)."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanListResponse:
    loans, total = await list_loans(db, current_user=current_user, page=page, page_size=page_size)
    return LoanListResponse(
        items=[LoanResponse.model_validate(loan) for loan in loans],
        total=total,
    )
