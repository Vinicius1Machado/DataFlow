import pytest
from pydantic import ValidationError

from app.schemas.auth import AuthCredentials
from app.services.password_service import PasswordService


def test_password_service_hashes_and_verifies_password() -> None:
    service = PasswordService()
    password_hash = service.hash_password("senha-segura")

    assert password_hash != "senha-segura"
    assert service.verify_password("senha-segura", password_hash)
    assert not service.verify_password("senha-errada", password_hash)


def test_auth_credentials_normalizes_username() -> None:
    credentials = AuthCredentials(username=" Analista_Dados ", password="123456")

    assert credentials.username == "analista_dados"


def test_auth_credentials_rejects_invalid_username() -> None:
    with pytest.raises(ValidationError):
        AuthCredentials(username="usuario ruim!", password="123456")
