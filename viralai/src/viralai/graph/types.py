"""
Research Graph type vocabulary.

The blueprint's full vision (Ch. "Recommendation 8" from the engineering review) spans
Genome -> Mutation -> Protein -> Domain -> Publication -> Drug -> Cancer -> Virus ->
Researcher -> Simulation -> AI Model. Phase 3 populates and tests a working subset —
VIRUS, GENOME, GENE, PROTEIN, MUTATION, PUBLICATION — because that's what Phase 1
(plugins) and Phase 2 (engines) actually produce data for today.

DRUG, CANCER, RESEARCHER, SIMULATION, and AI_MODEL are declared here for schema stability
(so later phases don't need a breaking rename) but are **not yet populated or tested** —
treat any graph query touching those types as unimplemented, not merely sparse.
"""

from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    # Populated and tested in Phase 3:
    VIRUS = "virus"
    GENOME = "genome"
    GENE = "gene"
    PROTEIN = "protein"
    MUTATION = "mutation"
    PUBLICATION = "publication"

    # Reserved for future phases -- not yet populated or tested:
    DOMAIN = "domain"
    DRUG = "drug"
    CANCER = "cancer"
    RESEARCHER = "researcher"
    SIMULATION = "simulation"
    AI_MODEL = "ai_model"


class RelationType(str, Enum):
    """Edge labels. Direction is always source -> target as named, e.g.
    (Genome) -[HAS_GENE]-> (Gene), (Mutation) -[LOCATED_IN_GENE]-> (Gene).
    """

    BELONGS_TO_VIRUS = "belongs_to_virus"
    HAS_GENE = "has_gene"
    LOCATED_IN_GENE = "located_in_gene"
    AFFECTS_PROTEIN = "affects_protein"
    CITED_BY = "cited_by"
    DESCRIBED_BY = "described_by"  # Mutation -> MutationKnowledge's source publication
