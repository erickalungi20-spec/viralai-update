"""
Knowledge Base entry models (Blueprint Ch.18.3).

Every entry carries an EvidenceLevel (reused from the IDM — Ch.18.5) so a consumer can
tell a computational prediction (Level IV) apart from something experimentally confirmed
(Level I) at a glance. No entry is exempt from citing a source; an entry with no citation
is not a knowledge base entry, it's a guess.
"""

from __future__ import annotations


from pydantic import BaseModel, Field, field_validator

from viralai.core.idm import EvidenceLevel


class LiteratureReference(BaseModel):
    """A citable source. Every other knowledge entry type links back to at least one."""

    reference_id: str
    citation: str  # human-readable citation text, e.g. "Smith et al. 2023, J Virol"
    doi: str | None = None
    pubmed_id: str | None = None
    url: str | None = None


class MutationKnowledge(BaseModel):
    """Curated, published information about a specific mutation — distinct from a
    computationally *detected* Mutation (idm.Mutation). This is what the Knowledge Base
    contributes on top of raw detection: known biological significance.
    """

    virus: str
    gene: str
    position: int = Field(ge=0)
    reference_base: str
    observed_base: str
    known_effect_summary: str
    evidence_level: EvidenceLevel
    reference_ids: list[str] = Field(min_length=1)

    @field_validator("reference_ids")
    @classmethod
    def must_cite_at_least_one_source(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("MutationKnowledge must cite at least one LiteratureReference")
        return value


class ProteinKnowledge(BaseModel):
    """Curated information about a protein or protein domain — functional role, not
    just the sequence coordinates a plugin already provides.
    """

    virus: str
    protein_id: str
    domain_name: str | None = None
    known_function_summary: str
    evidence_level: EvidenceLevel
    reference_ids: list[str] = Field(min_length=1)


class KnowledgeQuery(BaseModel):
    """A structured filter for querying the Knowledge Base — kept intentionally small
    (virus/gene/protein/min evidence level) rather than a generic query language, per the
    same "smallest thing that works" philosophy as Phase 0-2.
    """

    virus: str | None = None
    gene: str | None = None
    protein_id: str | None = None
    min_evidence_level: EvidenceLevel | None = None

    def matches_mutation_knowledge(self, entry: MutationKnowledge) -> bool:
        if self.virus and entry.virus != self.virus:
            return False
        if self.gene and entry.gene != self.gene:
            return False
        if self.min_evidence_level and not _evidence_at_least(
            entry.evidence_level, self.min_evidence_level
        ):
            return False
        return True


# Evidence levels are ordered I (strongest) through V (weakest) — Ch.18.5.
_EVIDENCE_ORDER: dict[EvidenceLevel, int] = {
    EvidenceLevel.LEVEL_I_EXPERIMENTAL: 1,
    EvidenceLevel.LEVEL_II_MULTI_STUDY: 2,
    EvidenceLevel.LEVEL_III_LIMITED: 3,
    EvidenceLevel.LEVEL_IV_COMPUTATIONAL: 4,
    EvidenceLevel.LEVEL_V_HYPOTHESIS: 5,
}


def _evidence_at_least(actual: EvidenceLevel, minimum: EvidenceLevel) -> bool:
    """True if `actual` is at least as strong as `minimum` (lower ordinal = stronger)."""
    return _EVIDENCE_ORDER[actual] <= _EVIDENCE_ORDER[minimum]
