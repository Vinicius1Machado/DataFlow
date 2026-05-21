import zipfile
from pathlib import Path
from typing import Any
import unittest

from app.services.package_service import PackageService


class FakeStorageService:
    def __init__(self) -> None:
        self.uploaded_path: str | None = None
        self.object_name: str | None = None

    def upload_file(self, local_path: str, object_name: str) -> str:
        self.uploaded_path = local_path
        self.object_name = object_name

        with zipfile.ZipFile(local_path) as package:
            assert sorted(package.namelist()) == [
                "README.md",
                "analysis.json",
                "requirements.txt",
                "script_tratamento.py",
            ]
            assert package.read("script_tratamento.py").decode("utf-8") == "print('ok')"
            assert package.read("README.md").decode("utf-8") == "# Uso"
            assert package.read("requirements.txt").decode("utf-8") == "pandas"

        return f"http://storage.local/{object_name}"


class PackageServiceTest(unittest.TestCase):
    def test_creates_and_uploads_result_package(self) -> None:
        storage_service = FakeStorageService()
        service = PackageService(storage_service=storage_service)

        url = service.create_result_package(
            job_id="job-123",
            script_code="print('ok')",
            manual_content="# Uso",
            requirements_txt="pandas",
            analysis_json={"rows": 1, "columns": 1},
        )

        self.assertEqual(url, "http://storage.local/results/job-123/resultado.zip")
        self.assertEqual(storage_service.object_name, "results/job-123/resultado.zip")
        self.assertIsNotNone(storage_service.uploaded_path)
        self.assertFalse(Path(storage_service.uploaded_path or "").exists())


if __name__ == "__main__":
    unittest.main()
