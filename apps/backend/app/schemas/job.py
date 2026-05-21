import uuid
from typing import Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DataJobCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    job_name: str = Field(min_length=1, max_length=255)
    file_name: str = Field(min_length=1, max_length=255)
    file_fingerprint: str = Field(min_length=64, max_length=64)
    file_type: str = Field(min_length=1, max_length=50)
    file_size: int = Field(ge=0)
    raw_file_url: str = Field(min_length=1)
    status: str = Field(default="pending", min_length=1, max_length=50)


class DataJobResponse(BaseModel):
    id: uuid.UUID
    job_name: str
    file_name: str
    file_fingerprint: str
    file_type: str
    file_size: int
    status: str
    raw_file_url: str
    result_package_url: str | None = None
    analysis_json: dict[str, Any] | None = None
    generated_script: str | None = None
    generated_manual: str | None = None
    requirements_txt: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataJobStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None = None
    result_package_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class N8NCallbackPayload(BaseModel):
    job_id: uuid.UUID
    status: str | None = Field(default=None, min_length=1, max_length=50)
    analysis: dict[str, Any] | None = None
    script_code: str | None = None
    manual_content: str | None = None
    requirements_txt: str | None = None
    result_package_url: str | None = None
    error_message: str | None = None
