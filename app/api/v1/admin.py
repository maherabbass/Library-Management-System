import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.user import RoleUpdate, UserResponse
from app.services.user import list_users, update_user_role

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_ADMIN_RESPONSES: dict = {
    401: {"description": "Missing, invalid, or expired Bearer token."},
    403: {"description": "Forbidden — Admin role required."},
}


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[require_role(UserRole.ADMIN)],
    summary="List all users",
    description=(
        "Returns every user account registered in the system, ordered by creation date.\n\n"
        "Use this endpoint to:\n"
        "- Review all accounts and their current roles.\n"
        "- Find user IDs for the `PATCH /admin/users/{id}/role` endpoint.\n\n"
        "**Requires:** Admin role."
    ),
    response_description="Array of all user profiles.",
    responses={
        **_ADMIN_RESPONSES,
    },
)
async def get_users(db: AsyncSession = Depends(get_db)) -> list[UserResponse]:
    users = await list_users(db)
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[require_role(UserRole.ADMIN)],
    summary="Change a user's role",
    description=(
        "Promotes or demotes a user by updating their RBAC role.\n\n"
        "**Available roles:**\n\n"
        "| Role | Description |\n"
        "|------|-------------|\n"
        "| `MEMBER` | Default role — can browse and borrow books |\n"
        "| `LIBRARIAN` | Can create/edit/delete books and manage all loans |\n"
        "| `ADMIN` | Full access including this user management endpoint |\n\n"
        "> **Warning:** demoting the last Admin account will lock everyone out of "
        "admin features.\n\n"
        "**Requires:** Admin role."
    ),
    response_description="The updated user profile reflecting the new role.",
    responses={
        **_ADMIN_RESPONSES,
        404: {"description": "User not found."},
        422: {
            "description": "Validation error — `role` must be one of `ADMIN`, `LIBRARIAN`, `MEMBER`."
        },
    },
)
async def patch_user_role(
    user_id: uuid.UUID,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await update_user_role(db, user_id, body.role)
    return UserResponse.model_validate(user)
