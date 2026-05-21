from typing import Any

from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    job_id: str = Field(min_length=1)
    file_url: str = Field(min_length=1)
    file_type: str = Field(min_length=1)


class ProfileResponse(BaseModel):
    job_id: str
    analysis: dict[str, Any]
