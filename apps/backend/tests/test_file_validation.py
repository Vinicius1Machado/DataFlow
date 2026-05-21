import pytest
from fastapi import HTTPException

from app.api.files import _calculate_file_fingerprint, _get_allowed_extension, _sanitize_job_name


@pytest.mark.parametrize("file_name", ["dados.csv", "dados.json", "dados.xml", "dados.parquet"])
def test_file_validation_accepts_allowed_extensions(file_name: str) -> None:
    assert _get_allowed_extension(file_name) in {".csv", ".json", ".xml", ".parquet"}


@pytest.mark.parametrize("file_name", ["malware.exe", "script.bat"])
def test_file_validation_rejects_disallowed_extensions(file_name: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _get_allowed_extension(file_name)

    assert exc_info.value.status_code == 400


def test_sanitize_job_name_normalizes_whitespace() -> None:
    assert _sanitize_job_name("  Limpeza   Clientes  ", "clientes.csv") == "Limpeza Clientes"


def test_file_fingerprint_is_stable_for_same_file(tmp_path) -> None:
    file_path = tmp_path / "clientes.csv"
    file_path.write_bytes(b"id,nome\n1,Ana\n")

    first_fingerprint = _calculate_file_fingerprint(str(file_path), "clientes.csv", file_path.stat().st_size)
    second_fingerprint = _calculate_file_fingerprint(str(file_path), "clientes.csv", file_path.stat().st_size)

    assert first_fingerprint == second_fingerprint
    assert len(first_fingerprint) == 64
