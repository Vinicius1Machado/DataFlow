import base64
import hashlib
import hmac
import secrets


class PasswordService:
    _algorithm = "pbkdf2_sha256"
    _iterations = 210_000
    _salt_size = 16

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(self._salt_size)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self._iterations)
        return "$".join(
            [
                self._algorithm,
                str(self._iterations),
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(digest).decode("ascii"),
            ]
        )

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
            if algorithm != self._algorithm:
                return False

            iterations = int(iterations_text)
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected_digest = base64.urlsafe_b64decode(digest_text.encode("ascii"))
            actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual_digest, expected_digest)
        except Exception:
            return False
