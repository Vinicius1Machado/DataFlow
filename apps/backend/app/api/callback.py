import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.job import DataJob
from app.schemas.job import N8NCallbackPayload
from app.services.package_service import PackageService, PackageServiceError
from app.services.script_security_service import ScriptSecurityService


router = APIRouter(prefix="/n8n", tags=["callback"])
logger = logging.getLogger(__name__)


class CallbackResponse(BaseModel):
    job_id: str
    status: str
    message: str


def _validate_webhook_secret(webhook_secret: str | None) -> None:
    if not webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook secret.")

    if not secrets.compare_digest(webhook_secret, settings.n8n_webhook_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret.")


@router.post("/callback", response_model=CallbackResponse)
def receive_n8n_callback(
    payload: N8NCallbackPayload,
    x_webhook_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CallbackResponse:
    _validate_webhook_secret(x_webhook_secret)

    data_job = db.get(DataJob, payload.job_id)
    if data_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    next_status = payload.status
    if payload.error_message:
        next_status = "FAILED"
    elif not next_status:
        next_status = "COMPLETED"

    script_code = payload.script_code
    security_result = None
    if script_code:
        security_result = ScriptSecurityService().validate_script(script_code)
        if not security_result["is_safe"]:
            next_status = "FAILED"
            script_code = None

    result_package_url = None if security_result and not security_result["is_safe"] else payload.result_package_url
    package_error_message = None
    if (
        script_code
        and payload.manual_content
        and payload.requirements_txt
        and next_status != "FAILED"
    ):
        try:
            result_package_url = PackageService().create_result_package(
                job_id=payload.job_id,
                script_code=script_code,
                manual_content=payload.manual_content,
                requirements_txt=payload.requirements_txt,
                analysis_json=payload.analysis,
            )
        except PackageServiceError as exc:
            next_status = "FAILED"
            package_error_message = str(exc)
            logger.error("Failed to create result package for job_id=%s", payload.job_id)

    data_job.status = next_status
    data_job.analysis_json = payload.analysis
    data_job.generated_script = script_code
    data_job.generated_manual = payload.manual_content
    data_job.requirements_txt = payload.requirements_txt
    data_job.result_package_url = result_package_url
    if security_result and not security_result["is_safe"]:
        blocked_patterns = ", ".join(security_result["blocked_patterns"])
        data_job.error_message = f"Generated script was blocked by security validation: {blocked_patterns}."
    elif package_error_message:
        data_job.error_message = package_error_message
    else:
        data_job.error_message = payload.error_message

    try:
        db.add(data_job)
        db.commit()
        db.refresh(data_job)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist n8n callback for job_id=%s", payload.job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist callback.",
        ) from exc

    logger.info("n8n callback processed for job_id=%s status=%s", data_job.id, data_job.status)

    return CallbackResponse(
        job_id=str(data_job.id),
        status=data_job.status,
        message="Callback processed successfully.",
    )
