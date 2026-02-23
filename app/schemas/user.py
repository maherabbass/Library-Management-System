import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole

_EXAMPLE_USER_ID = "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"


class UserResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Unique user identifier (UUID v4).")
    email: str = Field(..., description="User's verified email address.")
    name: str = Field(..., description="Display name from the OAuth provider.")
    role: UserRole = Field(
        ...,
        description="RBAC role: `ADMIN` | `LIBRARIAN` | `MEMBER`. New users start as `MEMBER`.",
    )
    oauth_provider: str | None = Field(
        None,
        description="OAuth provider used to sign in: `google` or `github`.",
    )
    created_at: datetime = Field(..., description="UTC timestamp when the account was created.")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_USER_ID,
                "email": "alice@example.com",
                "name": "Alice Smith",
                "role": "MEMBER",
                "oauth_provider": "google",
                "created_at": "2024-01-10T08:00:00Z",
            }
        },
    )


class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        description=(
            "JWT Bearer token. Include it in subsequent requests as:\n\n"
            "`Authorization: Bearer <access_token>`"
        ),
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        "bearer",
        description='Token scheme. Always `"bearer"`.',
        examples=["bearer"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxYjJjM2Q0ZS01ZjZhLTdiOGMtOWQwZS0xZjJhM2I0YzVkNmUiLCJleHAiOjE3MDU5MjE2MDB9.signature",
                "token_type": "bearer",
            }
        }
    )


class RoleUpdate(BaseModel):
    role: UserRole = Field(
        ...,
        description="The new role to assign to the user: `ADMIN` | `LIBRARIAN` | `MEMBER`.",
        examples=["LIBRARIAN"],
    )

    model_config = ConfigDict(json_schema_extra={"example": {"role": "LIBRARIAN"}})
