"""
Knowledge Base API (Blueprint Ch.30.3 Knowledge Base API): controlled access to curated,
cited biological knowledge -- distinct from the raw computational output of the Analysis
API.

Reads (GET) are open. Writes (POST) require an authenticated API key with at least
RESEARCHER role and are recorded in the audit log -- curated knowledge is exactly the
kind of "significant action" Ch.35.3 says must be tracked.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from viralai.api.auth import require_role
from viralai.api.dependencies import get_audit_logger, get_knowledge_base
from viralai.common.errors import ValidationError
from viralai.core.idm import EvidenceLevel
from viralai.knowledge.models import KnowledgeQuery, LiteratureReference, MutationKnowledge
from viralai.knowledge.store import KnowledgeBase
from viralai.security.api_keys import APIKeyRecord
from viralai.security.audit import AuditLogger
from viralai.security.roles import Role

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/references", response_model=LiteratureReference, status_code=201)
def add_reference(
    reference: LiteratureReference,
    kb: KnowledgeBase = Depends(get_knowledge_base),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> LiteratureReference:
    try:
        kb.add_reference(reference)
    except ValidationError as exc:
        audit.record(
            actor=api_key.label,
            action="knowledge.add_reference",
            resource=reference.reference_id,
            outcome="error",
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(
        actor=api_key.label, action="knowledge.add_reference", resource=reference.reference_id
    )
    return reference


@router.post("/mutations", response_model=MutationKnowledge, status_code=201)
def add_mutation_knowledge(
    entry: MutationKnowledge,
    kb: KnowledgeBase = Depends(get_knowledge_base),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> MutationKnowledge:
    resource = f"{entry.virus}/{entry.gene}/{entry.position}"
    try:
        kb.add_mutation_knowledge(entry)
    except ValidationError as exc:
        audit.record(
            actor=api_key.label, action="knowledge.add_mutation", resource=resource, outcome="error"
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit.record(actor=api_key.label, action="knowledge.add_mutation", resource=resource)
    return entry


@router.get("/mutations", response_model=list[MutationKnowledge])
def query_mutation_knowledge(
    virus: str | None = None,
    gene: str | None = None,
    min_evidence_level: EvidenceLevel | None = Query(default=None),
    kb: KnowledgeBase = Depends(get_knowledge_base),
) -> list[MutationKnowledge]:
    query = KnowledgeQuery(virus=virus, gene=gene, min_evidence_level=min_evidence_level)
    return kb.query_mutation_knowledge(query)
