"""
API Key store (Blueprint Ch.35.3 Authentication).

Design choice, stated explicitly (see ADR-012): API keys are hashed with plain
SHA-256, not bcrypt/argon2. That's deliberate, not a shortcut -- bcrypt-family
algorithms are intentionally *slow* to resist brute-forcing low-entropy human
passwords. API keys here are generated with `secrets.token_urlsafe(32)` (256 bits of
entropy) -- brute-forcing is already infeasible, and a slow hash would only cost
legitimate lookups performance for no security benefit. This is the same reasoning
GitHub, Stripe, and AWS use for their own API token storage.

The raw key is shown to the caller exactly once, at issuance. Only its hash is ever
persisted -- if a key is lost, it must be revoked and reissued, not "recovered".
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from viralai.common.errors import ValidationError
from viralai.common.ids import new_id
from viralai.common.logging import get_logger
from viralai.security.roles import Role

logger = get_logger("security.api_keys")


class APIKeyRecord(BaseModel):
    """What's persisted. Never contains the raw key -- only its SHA-256 hash."""

    key_id: str = Field(default_factory=lambda: new_id("key"))
    hashed_key: str
    label: str
    role: Role
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False


class APIKeyMetadata(BaseModel):
    """Safe-to-return API-key metadata. Deliberately excludes the stored hash."""

    key_id: str
    label: str
    role: Role
    created_at: datetime
    revoked: bool

    @classmethod
    def from_record(cls, record: APIKeyRecord) -> "APIKeyMetadata":
        return cls(
            key_id=record.key_id,
            label=record.label,
            role=record.role,
            created_at=record.created_at,
            revoked=record.revoked,
        )


class APIKeyStore:
    """File-backed API key store, same pattern as every other registry in this
    codebase. One JSON file holding all key records (hashes only).
    """

    def __init__(self, storage_path: Path | str) -> None:
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, APIKeyRecord] = {}
        self._load()

    def issue_key(self, label: str, role: Role) -> tuple[str, APIKeyRecord]:
        """Create a new API key. Returns (raw_key, record) -- the raw key is returned
        ONLY here; it cannot be retrieved again after this call returns.
        """
        raw_key = secrets.token_urlsafe(32)
        record = APIKeyRecord(hashed_key=_hash_key(raw_key), label=label, role=role)
        self._records[record.key_id] = record
        self._save()
        logger.info("API key issued: id=%s label=%s role=%s", record.key_id, label, role.name)
        return raw_key, record

    def verify_key(self, raw_key: str) -> APIKeyRecord | None:
        """Return the matching, non-revoked APIKeyRecord, or None if the key is
        invalid, unknown, or revoked. Never raises on a bad key -- an invalid API key
        is an expected input for this method, not an exceptional condition.
        """
        hashed = _hash_key(raw_key)
        for record in self._records.values():
            if record.hashed_key == hashed and not record.revoked:
                return record
        return None

    def revoke_key(self, key_id: str) -> None:
        if key_id not in self._records:
            raise ValidationError(f"No API key with id '{key_id}'")
        self._records[key_id].revoked = True
        self._save()
        logger.info("API key revoked: id=%s", key_id)

    def list_keys(self) -> list[APIKeyMetadata]:
        """Metadata only -- never exposes hashes or raw keys in bulk listings."""
        return [APIKeyMetadata.from_record(record) for record in self._records.values()]

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        self._records = {item["key_id"]: APIKeyRecord(**item) for item in raw}

    def _save(self) -> None:
        self._storage_path.write_text(
            json.dumps([r.model_dump(mode="json") for r in self._records.values()], indent=2),
            encoding="utf-8",
        )


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
