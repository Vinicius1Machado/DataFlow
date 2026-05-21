import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.job import DataJob
from app.models.user import AppUser
from app.schemas.job import DataJobResponse


router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobDownloadResponse(BaseModel):
    job_id: uuid.UUID
    result_package_url: str


class JobDeleteResponse(BaseModel):
    job_id: uuid.UUID
    message: str


@router.get("/{job_id}/download", response_model=JobDownloadResponse)
def get_job_download_url(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
) -> JobDownloadResponse:
    data_job = db.get(DataJob, job_id)
    if data_job is None or data_job.user_id != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if not data_job.result_package_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result package is not available.")

    return JobDownloadResponse(job_id=data_job.id, result_package_url=data_job.result_package_url)


@router.get("/{job_id}", response_model=DataJobResponse)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
) -> DataJob:
    data_job = db.get(DataJob, job_id)
    if data_job is None or data_job.user_id != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    return data_job


@router.delete("/{job_id}", response_model=JobDeleteResponse)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
) -> JobDeleteResponse:
    data_job = db.get(DataJob, job_id)
    if data_job is None or data_job.user_id != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    db.delete(data_job)
    db.commit()

    return JobDeleteResponse(job_id=job_id, message="Job removed from history.")


@router.get("", response_model=list[DataJobResponse])
def list_jobs(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
) -> list[DataJob]:
    statement = (
        select(DataJob)
        .where(DataJob.user_id == current_user.username)
        .order_by(DataJob.created_at.desc())
        .limit(limit)
    )

    return list(db.scalars(statement).all())
