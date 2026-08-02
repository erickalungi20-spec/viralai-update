"""
Admin API: API key issuance/listing/revocation. All operations require ADMIN role.

Bootstrap note: there is deliberately no unauthenticated "create the first admin key"
endpoint here -- that would be a standing security hole. The first admin key is issued
out-of-band via the CLI (`viralai issue-api-key --label ... --role admin`), which
operates directly against the local APIKeyStore file with no HTTP/auth involved, the
same way `django-admin createsuperuser` or similar tools bootstrap the first privileged
account. See ADR-012.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from viralai.api.auth import get_api_key_store, require_role
from viralai.api.dependencies import get_audit_logger
from viralai.common.errors import ValidationError
from viralai.security.api_keys import APIKeyMetadata, APIKeyRecord, APIKeyStore
from viralai.security.audit import AuditLogger
from viralai.security.roles import Role

router = APIRouter(prefix="/admin/api-keys", tags=["admin"])


class IssueAPIKeyRequest(BaseModel):
    label: str
    role: Role

    @field_validator("role", mode="before")
    @classmethod
    def _accept_role_by_name(cls, value: object) -> object:
        """Accept 'admin'/'researcher'/'viewer' (any case) as well as the raw integer
        value -- much friendlier for API clients than requiring them to know Role's
        underlying integer encoding.
        """
        if isinstance(value, str) and not value.isdigit():
            try:
                return Role[value.upper()]
            except KeyError:
                raise ValueError(
                    f"Unknown role '{value}', expected one of {[r.name.lower() for r in Role]}"
                ) from None
        return value


class IssuedAPIKeyResponse(BaseModel):
    raw_key: str
    record: APIKeyMetadata


@router.post("", response_model=IssuedAPIKeyResponse, status_code=201)
def issue_api_key(
    request: IssueAPIKeyRequest,
    store: APIKeyStore = Depends(get_api_key_store),
    api_key: APIKeyRecord = Depends(require_role(Role.ADMIN)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> IssuedAPIKeyResponse:
    raw_key, record = store.issue_key(request.label, request.role)
    audit.record(actor=api_key.label, action="admin.issue_api_key", resource=record.key_id)
    return IssuedAPIKeyResponse(raw_key=raw_key, record=APIKeyMetadata.from_record(record))


@router.get("", response_model=list[APIKeyMetadata])
def list_api_keys(
    store: APIKeyStore = Depends(get_api_key_store),
    api_key: APIKeyRecord = Depends(require_role(Role.ADMIN)),
) -> list[APIKeyMetadata]:
    return store.list_keys()


@router.post("/{key_id}/revoke", status_code=204)
def revoke_api_key(
    key_id: str,
    store: APIKeyStore = Depends(get_api_key_store),
    api_key: APIKeyRecord = Depends(require_role(Role.ADMIN)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    try:
        store.revoke_key(key_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit.record(actor=api_key.label, action="admin.revoke_api_key", resource=key_id)
