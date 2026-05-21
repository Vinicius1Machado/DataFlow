import pytest
from fastapi import HTTPException

from app.api.files import _get_allowed_extension


@pytest.mark.parametrize("file_name", ["dados.csv", "dados.json", "dados.xml", "dados.parquet"])
def test_file_validation_accepts_allowed_extensions(file_name: str) -> None:
    assert _get_allowed_extension(file_name) in {".csv", ".json", ".xml", ".parquet"}


@pytest.mark.parametrize("file_name", ["malware.exe", "script.bat"])
def test_file_validation_rejects_disallowed_extensions(file_name: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _get_allowed_extension(file_name)

    assert exc_info.value.status_code == 400
