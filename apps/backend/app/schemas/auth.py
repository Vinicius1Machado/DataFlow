from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must contain only letters, numbers, hyphen or underscore.")
        return normalized


class RegisterCredentials(AuthCredentials):
    full_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=160)
    role: str | None = Field(default=None, max_length=120)

    @field_validator("full_name", "email", "organization", "role")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.strip().split())
        return normalized or None

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Email must be valid.")
        return normalized


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=160)
    role: str | None = Field(default=None, max_length=120)

    @field_validator("full_name", "email", "organization", "role")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.strip().split())
        return normalized or None

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Email must be valid.")
        return normalized


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str | None = None
    email: str | None = None
    organization: str | None = None
    role: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
