from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
import os
from secrets import randbelow, token_hex


CODE_EXPIRATION_MINUTES = 10
MAX_VERIFICATION_ATTEMPTS = 5


def generate_code() -> str:
    """Gera um código numérico de seis dígitos."""
    return f"{randbelow(1_000_000):06d}"


def generate_salt() -> str:
    """Gera um salt aleatório para o código."""
    return token_hex(16)


def hash_code(code: str, salt: str) -> str:
    """Calcula o hash do código com salt."""
    secret = os.environ.get("EMAIL_VERIFICATION_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "EMAIL_VERIFICATION_SECRET deve conter pelo menos 32 caracteres"
        )
    return hmac_new(
        secret.encode(),
        f"{salt}:{code}".encode(),
        sha256,
    ).hexdigest()


def verify_code(code: str, salt: str, expected_hash: str) -> bool:
    """Compara o hash do código informado."""
    actual_hash = hash_code(code, salt)
    return compare_digest(actual_hash, expected_hash)


def expiration_time() -> datetime:
    """Define o horário de expiração do código."""
    return datetime.now(timezone.utc) + timedelta(
        minutes=CODE_EXPIRATION_MINUTES
    )


def is_expired(expires_at: datetime) -> bool:
    """Verifica se o código expirou."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) >= expires_at
