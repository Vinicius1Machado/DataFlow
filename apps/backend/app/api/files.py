import hashlib
import re
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.job import DataJob
from app.models.user import AppUser
from app.services.n8n_service import N8NService, N8NServiceError, get_n8n_service
from app.services.storage_service import StorageService, StorageServiceError


router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_EXTENSIONS = {".csv", ".parquet", ".json", ".xml"}
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024

STATUS_SENT_TO_N8N = "SENT_TO_N8N"
STATUS_N8N_ERROR = "N8N_ERROR"
STATUS_FAILED = "FAILED"


class UploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str


def _sanitize_job_name(job_name: str, fallback: str) -> str:
    sanitized_name = re.sub(r"\s+", " ", job_name.strip())
    if not sanitized_name:
        sanitized_name = Path(fallback).stem
    if len(sanitized_name) > 255:
        sanitized_name = sanitized_name[:255].rstrip()
    return sanitized_name or "Processamento"


def _sanitize_file_name(file_name: str) -> str:
    original_name = Path(file_name or "uploaded-file").name
    sanitized_name = re.sub(r"[^A-Za-z0-9._-]", "_", original_name).strip("._")
    return sanitized_name or "uploaded-file"


def _get_allowed_extension(file_name: str) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed extensions: {allowed}.",
        )
    return extension


def _looks_like_allowed_file(temp_path: str, file_extension: str) -> bool:
    path = Path(temp_path)
    with path.open("rb") as file:
        head = file.read(4096)
        if file_extension == ".parquet":
            file.seek(max(path.stat().st_size - 4, 0))
            tail = file.read(4)
        else:
            tail = b""

    if not head:
        return False

    if file_extension == ".parquet":
        return head.startswith(b"PAR1") or tail == b"PAR1"

    if b"\x00" in head:
        return False

    sample = head.lstrip(b"\xef\xbb\xbf").lstrip()
    if file_extension == ".json":
        return sample.startswith((b"{", b"["))
    if file_extension == ".xml":
        return sample.startswith((b"<?xml", b"<"))
    if file_extension == ".csv":
        return any(delimiter in head for delimiter in (b",", b";", b"\t")) or b"\n" in head

    return False


async def _write_upload_to_temp_file(upload_file: UploadFile) -> tuple[str, int]:
    temp_file = tempfile.NamedTemporaryFile(prefix="dsg-upload-", suffix=".tmp", delete=False)
    temp_path = temp_file.name
    file_size = 0

    try:
        with temp_file:
            while chunk := await upload_file.read(UPLOAD_CHUNK_SIZE_BYTES):
                file_size += len(chunk)
                if file_size > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds the maximum allowed size of 50 MB.",
                    )
                temp_file.write(chunk)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise

    return temp_path, file_size


def _calculate_file_fingerprint(temp_path: str, file_name: str, file_size: int) -> str:
    digest = hashlib.sha256()
    digest.update(file_name.lower().encode("utf-8"))
    digest.update(str(file_size).encode("utf-8"))

    with Path(temp_path).open("rb") as file:
        for chunk in iter(lambda: file.read(UPLOAD_CHUNK_SIZE_BYTES), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _try_update_job_status(db: Session, data_job: DataJob, status_value: str, error_message: str) -> None:
    try:
        data_job.status = status_value
        data_job.error_message = error_message
        db.add(data_job)
        db.commit()
        db.refresh(data_job)
    except Exception:
        db.rollback()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: Annotated[UploadFile, File()],
    job_name: Annotated[str, Form(min_length=1, max_length=255)],
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    n8n_service: N8NService = Depends(get_n8n_service),
) -> UploadResponse:
    sanitized_file_name = _sanitize_file_name(file.filename or "")
    sanitized_job_name = _sanitize_job_name(job_name, sanitized_file_name)
    file_extension = _get_allowed_extension(sanitized_file_name)
    file_type = file_extension.lstrip(".")
    temp_path: str | None = None
    data_job: DataJob | None = None

    try:
        temp_path, file_size = await _write_upload_to_temp_file(file)
        if file_size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

        if not _looks_like_allowed_file(temp_path, file_extension):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match the expected format.",
            )

        file_fingerprint = _calculate_file_fingerprint(temp_path, sanitized_file_name, file_size)
        existing_job = db.scalar(
            select(DataJob)
            .where(DataJob.user_id == current_user.username)
            .where(DataJob.file_fingerprint == file_fingerprint)
        )
        if existing_job is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Este arquivo ja foi processado neste usuario. "
                    f"Registro existente: {existing_job.job_name}."
                ),
            )

        storage_service = StorageService()
        job_id = uuid.uuid4()
        object_name = f"raw/{job_id}/{sanitized_file_name}"
        file_url = storage_service.upload_file(temp_path, object_name)
        worker_file_url = storage_service.generate_object_url(
            object_name,
            settings.minio_worker_endpoint or settings.minio_public_endpoint,
        )

        data_job = DataJob(
            id=job_id,
            user_id=current_user.username,
            job_name=sanitized_job_name,
            file_name=sanitized_file_name,
            file_fingerprint=file_fingerprint,
            file_type=file_type,
            file_size=file_size,
            status=STATUS_SENT_TO_N8N,
            raw_file_url=file_url,
        )
        db.add(data_job)
        db.commit()
        db.refresh(data_job)

        payload = {
            "job_id": str(data_job.id),
            "user_id": data_job.user_id,
            "job_name": data_job.job_name,
            "file_name": data_job.file_name,
            "file_type": data_job.file_type,
            "file_size": data_job.file_size,
            "file_url": worker_file_url,
            "callback_url": settings.backend_callback_url,
        }

        try:
            await n8n_service.send_job_to_n8n(payload)
        except N8NServiceError as exc:
            _try_update_job_status(db, data_job, STATUS_N8N_ERROR, str(exc))
            return UploadResponse(
                job_id=data_job.id,
                status=data_job.status,
                message="File was uploaded, but n8n notification failed.",
            )

        return UploadResponse(
            job_id=data_job.id,
            status=data_job.status,
            message="File uploaded and sent to n8n.",
        )
    except HTTPException:
        raise
    except StorageServiceError as exc:
        db.rollback()
        if data_job is not None:
            _try_update_job_status(db, data_job, STATUS_FAILED, str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este arquivo ja foi processado neste usuario.",
        ) from exc
    except Exception as exc:
        db.rollback()
        if data_job is not None:
            _try_update_job_status(db, data_job, STATUS_FAILED, "Unexpected upload processing error.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected upload processing error.",
        ) from exc
    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
        await file.close()
