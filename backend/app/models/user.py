"""User model for authentication and authorisation."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class User(Document):
    """Application user account."""

    email: Indexed(EmailStr, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    role: str = Field(default="analyst", pattern=r"^(admin|analyst|viewer)$")
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<User {self.email}>"
