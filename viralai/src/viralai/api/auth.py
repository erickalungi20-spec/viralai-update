"""
FastAPI auth dependencies: verifies the X-API-Key header against the APIKeyStore and
enforces minimum role via `require_role`.
"""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from viralai.security.api_keys import APIKeyRecord, APIKeyStore
from viralai.security.roles import Role


@lru_cache
def _default_store_path() -> str:
    return os.environ.get("VIRALAI_DATA_DIR", ".viralai_api_data") + "/api_keys.json"


@lru_cache
def get_api_key_store() -> APIKeyStore:
    return APIKeyStore(storage_path=_default_store_path())


def reset_auth_cache() -> None:
    _default_store_path.cache_clear()
    get_api_key_store.cache_clear()


def get_current_api_key(
    x_api_key: str | None = Header(default=None), store: APIKeyStore = Depends(get_api_key_store)
) -> APIKeyRecord:
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    record = store.verify_key(x_api_key)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return record


def require_role(minimum: Role):
    """Dependency factory: `Depends(require_role(Role.RESEARCHER))` rejects any API key
    whose role is below `minimum`, with a 403 (key is valid, just insufficient
    privilege) rather than a 401 (which means "you're not authenticated at all").
    """

    def _check(api_key: APIKeyRecord = Depends(get_current_api_key)) -> APIKeyRecord:
        if api_key.role < minimum:
            raise HTTPException(
                status_code=403,
                detail=f"This operation requires role '{minimum.name}' or higher; "
                f"your key has role '{api_key.role.name}'",
            )
        return api_key

    return _check
