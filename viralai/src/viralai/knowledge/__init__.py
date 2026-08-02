"""
Phase 3 Knowledge Base: curated, evidence-level-tagged biological knowledge, distinct
from the computationally-detected output of Phase 2's engines.
"""

from viralai.knowledge.models import (
    KnowledgeQuery,
    LiteratureReference,
    MutationKnowledge,
    ProteinKnowledge,
)
from viralai.knowledge.store import KnowledgeBase

__all__ = [
    "LiteratureReference",
    "MutationKnowledge",
    "ProteinKnowledge",
    "KnowledgeQuery",
    "KnowledgeBase",
]
