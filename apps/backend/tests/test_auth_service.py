import pytest
from pydantic import ValidationError

from app.schemas.auth import AuthCredentials, RegisterCredentials, UserProfileUpdate
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


def test_register_credentials_accepts_profile_fields() -> None:
    credentials = RegisterCredentials(
        username=" Analista_Dados ",
        password="123456",
        full_name="  Ana   Dados  ",
        email="ANA@EXEMPLO.COM",
        organization="Time BI",
        role="Analista",
    )

    assert credentials.username == "analista_dados"
    assert credentials.full_name == "Ana Dados"
    assert credentials.email == "ana@exemplo.com"


def test_register_credentials_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterCredentials(username="analista", password="123456", email="email-invalido")


def test_user_profile_update_normalizes_optional_fields() -> None:
    payload = UserProfileUpdate(
        full_name="  Ana   Dados  ",
        email="ANA@EXEMPLO.COM",
        organization="  Time   BI  ",
        role="",
    )

    assert payload.full_name == "Ana Dados"
    assert payload.email == "ana@exemplo.com"
    assert payload.organization == "Time BI"
    assert payload.role is None
