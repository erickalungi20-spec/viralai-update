import pytest

from viralai.common.errors import ValidationError
from viralai.security.api_keys import APIKeyStore
from viralai.security.roles import Role


def test_issue_key_returns_raw_key_and_record(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    raw_key, record = store.issue_key("test-key", Role.RESEARCHER)

    assert isinstance(raw_key, str)
    assert len(raw_key) > 20
    assert record.label == "test-key"
    assert record.role == Role.RESEARCHER
    assert record.revoked is False


def test_raw_key_is_never_persisted_in_plaintext(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    raw_key, record = store.issue_key("test-key", Role.RESEARCHER)

    stored_content = (tmp_path / "keys.json").read_text()
    assert raw_key not in stored_content
    assert record.hashed_key in stored_content


def test_verify_key_returns_matching_record(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    raw_key, record = store.issue_key("test-key", Role.ADMIN)

    verified = store.verify_key(raw_key)

    assert verified is not None
    assert verified.key_id == record.key_id


def test_verify_invalid_key_returns_none(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    assert store.verify_key("totally-invalid-key") is None


def test_revoked_key_fails_verification(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    raw_key, record = store.issue_key("test-key", Role.RESEARCHER)

    store.revoke_key(record.key_id)

    assert store.verify_key(raw_key) is None


def test_revoke_unknown_key_raises(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    with pytest.raises(ValidationError):
        store.revoke_key("nonexistent")


def test_list_keys_returns_all_issued_keys(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    store.issue_key("key-1", Role.VIEWER)
    store.issue_key("key-2", Role.ADMIN)

    keys = store.list_keys()

    assert len(keys) == 2
    assert {k.label for k in keys} == {"key-1", "key-2"}
    assert all(not hasattr(key, "hashed_key") for key in keys)


def test_keys_persist_across_reload(tmp_path):
    store1 = APIKeyStore(tmp_path / "keys.json")
    raw_key, record = store1.issue_key("test-key", Role.RESEARCHER)

    store2 = APIKeyStore(tmp_path / "keys.json")

    verified = store2.verify_key(raw_key)
    assert verified is not None
    assert verified.key_id == record.key_id


def test_different_keys_have_different_hashes(tmp_path):
    store = APIKeyStore(tmp_path / "keys.json")
    _, record1 = store.issue_key("key-1", Role.VIEWER)
    _, record2 = store.issue_key("key-2", Role.VIEWER)

    assert record1.hashed_key != record2.hashed_key
