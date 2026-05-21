import json
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, Protocol


class PackageServiceError(Exception):
    pass


class StorageUploader(Protocol):
    def upload_file(self, local_path: str, object_name: str) -> str:
        pass


class PackageService:
    def __init__(self, storage_service: StorageUploader | None = None) -> None:
        if storage_service is None:
            from app.services.storage_service import StorageService

            storage_service = StorageService()
        self.storage_service = storage_service

    def create_result_package(
        self,
        job_id: uuid.UUID | str,
        script_code: str,
        manual_content: str,
        requirements_txt: str,
        analysis_json: dict[str, Any] | None,
    ) -> str:
        temp_path: str | None = None
        object_name = f"results/{job_id}/resultado.zip"

        try:
            with tempfile.NamedTemporaryFile(prefix="dsg-result-", suffix=".zip", delete=False) as temp_file:
                temp_path = temp_file.name

            self._write_zip(
                zip_path=temp_path,
                script_code=script_code,
                manual_content=manual_content,
                requirements_txt=requirements_txt,
                analysis_json=analysis_json or {},
            )
            return self.storage_service.upload_file(temp_path, object_name)
        except Exception as exc:
            raise PackageServiceError("Failed to create or upload result package.") from exc
        finally:
            if temp_path is not None:
                Path(temp_path).unlink(missing_ok=True)

    def _write_zip(
        self,
        zip_path: str,
        script_code: str,
        manual_content: str,
        requirements_txt: str,
        analysis_json: dict[str, Any],
    ) -> None:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr("script_tratamento.py", script_code)
            package.writestr("README.md", manual_content)
            package.writestr("requirements.txt", requirements_txt)
            package.writestr(
                "analysis.json",
                json.dumps(analysis_json, ensure_ascii=False, indent=2, default=str),
            )
