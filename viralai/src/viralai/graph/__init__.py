"""
Phase 3 Research Graph: an in-memory (networkx-backed) typed graph connecting Virus,
Gene, Mutation, Protein, and Publication entities, populated from Phase 1 plugin data,
Phase 2 engine output, and this phase's own Knowledge Base.
"""

from viralai.graph.ingestion import (
    ingest_knowledge_base,
    ingest_mutations,
    ingest_protein_mutations,
    ingest_virus_and_genes,
)
from viralai.graph.research_graph import ResearchGraph
from viralai.graph.types import NodeType, RelationType

__all__ = [
    "ResearchGraph",
    "NodeType",
    "RelationType",
    "ingest_virus_and_genes",
    "ingest_mutations",
    "ingest_protein_mutations",
    "ingest_knowledge_base",
]
