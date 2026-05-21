from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.core.config import settings


class StorageServiceError(Exception):
    pass


class StorageService:
    def __init__(self) -> None:
        self.bucket_name = settings.minio_bucket
        self.client = self._create_client()
        if settings.is_local_environment:
            self._ensure_bucket_exists()

    def _create_client(self) -> Any:
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_root_user,
            aws_secret_access_key=settings.minio_root_password,
            region_name=settings.minio_region,
        )

    def upload_file(self, local_path: str, object_name: str) -> str:
        from botocore.exceptions import BotoCoreError, ClientError

        path = Path(local_path)
        if not path.is_file():
            raise StorageServiceError(f"Local file not found: {local_path}")

        try:
            self.client.upload_file(str(path), self.bucket_name, object_name)
        except (BotoCoreError, ClientError) as exc:
            raise StorageServiceError(f"Failed to upload file to object '{object_name}'.") from exc

        return self.generate_object_url(object_name)

    def upload_bytes(self, content: bytes, object_name: str, content_type: str | None = None) -> str:
        from botocore.exceptions import BotoCoreError, ClientError

        put_kwargs: dict[str, object] = {
            "Bucket": self.bucket_name,
            "Key": object_name,
            "Body": content,
        }
        if content_type:
            put_kwargs["ContentType"] = content_type

        try:
            self.client.put_object(**put_kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise StorageServiceError(f"Failed to upload bytes to object '{object_name}'.") from exc

        return self.generate_object_url(object_name)

    def generate_object_url(self, object_name: str, endpoint: str | None = None) -> str:
        encoded_object_name = quote(object_name.lstrip("/"), safe="/")
        public_endpoint = (endpoint or settings.minio_public_endpoint).rstrip("/")
        return f"{public_endpoint}/{self.bucket_name}/{encoded_object_name}"

    def _ensure_bucket_exists(self) -> None:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise StorageServiceError(f"Failed to check bucket '{self.bucket_name}'.") from exc
            self._create_bucket()
        except BotoCoreError as exc:
            raise StorageServiceError(f"Failed to connect to storage bucket '{self.bucket_name}'.") from exc

    def _create_bucket(self) -> None:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            self.client.create_bucket(Bucket=self.bucket_name)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                return
            raise StorageServiceError(f"Failed to create bucket '{self.bucket_name}'.") from exc
        except BotoCoreError as exc:
            raise StorageServiceError(f"Failed to create bucket '{self.bucket_name}'.") from exc


def get_storage_service() -> StorageService:
    return StorageService()
