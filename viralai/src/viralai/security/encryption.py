"""
Encryption at rest (Blueprint Ch.35.3 Data Protection).

Symmetric encryption (Fernet: AES-128-CBC + HMAC, from the `cryptography` package) for
file contents before they touch disk. This wraps individual file read/write operations
rather than replacing every store's storage format wholesale -- a registry can opt in by
calling `write_encrypted`/`read_encrypted` instead of `Path.write_text`/`read_text`.

Key management, stated honestly: the encryption key is read from the
VIRALAI_ENCRYPTION_KEY environment variable. If it's not set, a key is generated at
runtime and a loud warning is logged -- this is fine for local development and tests
(each process gets its own ephemeral key, data encrypted in one run is unreadable in the
next, which is obviously wrong for real persistent use) but is NOT a real key management
solution. A production deployment must set VIRALAI_ENCRYPTION_KEY from a real secret
manager (AWS KMS, HashiCorp Vault, etc.) -- integrating with one of those is real,
separate infrastructure work not undertaken here. See ADR-012.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from viralai.common.errors import ConfigurationError, ValidationError
from viralai.common.logging import get_logger

logger = get_logger("security.encryption")

_ENV_VAR = "VIRALAI_ENCRYPTION_KEY"
_ephemeral_key_cache: bytes | None = None


def _is_production() -> bool:
    return os.environ.get("VIRALAI_ENVIRONMENT", "development").lower() in {
        "production",
        "prod",
    }


def validate_encryption_configuration() -> None:
    """Validate encryption-key configuration without generating a development key.

    Production must receive a persistent Fernet key from the deployment's secret
    manager. Development and tests retain the ephemeral fallback for convenience.
    """
    env_key = os.environ.get(_ENV_VAR)
    if not env_key:
        if _is_production():
            raise ConfigurationError(
                f"{_ENV_VAR} must be supplied by a secret manager when "
                "VIRALAI_ENVIRONMENT=production"
            )
        return
    try:
        Fernet(env_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{_ENV_VAR} is not a valid Fernet key") from exc


def get_encryption_key() -> bytes:
    """Return the active Fernet key. Reads VIRALAI_ENCRYPTION_KEY if set; otherwise
    generates and caches an ephemeral key for this process, logging a loud warning.
    """
    global _ephemeral_key_cache

    validate_encryption_configuration()
    env_key = os.environ.get(_ENV_VAR)
    if env_key:
        return env_key.encode("utf-8")

    if _ephemeral_key_cache is None:
        _ephemeral_key_cache = Fernet.generate_key()
        logger.warning(
            "%s is not set -- generated an EPHEMERAL encryption key for this process only. "
            "Data encrypted now will NOT be readable after this process exits. Set %s to a "
            "persistent, securely-managed key before using encryption for real data.",
            _ENV_VAR,
            _ENV_VAR,
        )
    return _ephemeral_key_cache


def encrypt_text(plaintext: str) -> bytes:
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_text(ciphertext: bytes) -> str:
    fernet = Fernet(get_encryption_key())
    try:
        return fernet.decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise ValidationError(
            "Failed to decrypt data -- wrong encryption key, or the data was encrypted "
            "with a different key (e.g. an ephemeral key from a prior process run)."
        ) from exc


def write_encrypted(path: Path | str, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encrypt_text(text))


def read_encrypted(path: Path | str) -> str:
    path = Path(path)
    if not path.exists():
        raise ValidationError(f"No encrypted file at {path}")
    return decrypt_text(path.read_bytes())
