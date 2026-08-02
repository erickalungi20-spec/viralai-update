import pytest
from cryptography.fernet import Fernet

from viralai.common.errors import ConfigurationError, ValidationError
from viralai.security.encryption import (
    decrypt_text,
    encrypt_text,
    read_encrypted,
    validate_encryption_configuration,
    write_encrypted,
)


@pytest.fixture(autouse=True)
def fixed_encryption_key(monkeypatch):
    """Every test in this file uses a fixed key via the env var, so encrypt/decrypt
    round trips are deterministic and independent of the ephemeral-key-per-process
    fallback behavior (which is tested separately, explicitly).
    """
    monkeypatch.setenv("VIRALAI_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))


def test_encrypt_decrypt_round_trip():
    plaintext = "sensitive research data"
    ciphertext = encrypt_text(plaintext)

    assert ciphertext != plaintext.encode()
    assert decrypt_text(ciphertext) == plaintext


def test_ciphertext_does_not_contain_plaintext():
    plaintext = "a very specific secret string"
    ciphertext = encrypt_text(plaintext)
    assert b"a very specific secret string" not in ciphertext


def test_decrypt_with_wrong_key_raises(monkeypatch):
    ciphertext = encrypt_text("some data")

    monkeypatch.setenv("VIRALAI_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))

    with pytest.raises(ValidationError):
        decrypt_text(ciphertext)


def test_write_and_read_encrypted_file_round_trip(tmp_path):
    path = tmp_path / "secret.enc"
    write_encrypted(path, "confidential content")

    assert read_encrypted(path) == "confidential content"


def test_encrypted_file_is_not_plaintext_on_disk(tmp_path):
    path = tmp_path / "secret.enc"
    write_encrypted(path, "confidential content")

    raw_bytes = path.read_bytes()
    assert b"confidential content" not in raw_bytes


def test_read_encrypted_missing_file_raises(tmp_path):
    with pytest.raises(ValidationError):
        read_encrypted(tmp_path / "nonexistent.enc")


def test_ephemeral_key_generated_when_env_var_unset(monkeypatch):
    """Without VIRALAI_ENCRYPTION_KEY set, encryption should still work within the
    same process (using a generated ephemeral key), with a warning logged -- this test
    checks the functional round trip, not the warning itself.
    """
    monkeypatch.delenv("VIRALAI_ENCRYPTION_KEY", raising=False)
    import viralai.security.encryption as encryption_module

    encryption_module._ephemeral_key_cache = None  # reset the module-level cache

    ciphertext = encrypt_text("ephemeral test")
    assert decrypt_text(ciphertext) == "ephemeral test"

    encryption_module._ephemeral_key_cache = None  # clean up after the test


def test_production_requires_a_persistent_encryption_key(monkeypatch):
    monkeypatch.delenv("VIRALAI_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("VIRALAI_ENVIRONMENT", "production")

    with pytest.raises(ConfigurationError, match="VIRALAI_ENCRYPTION_KEY"):
        validate_encryption_configuration()
