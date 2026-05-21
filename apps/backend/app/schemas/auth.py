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


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
