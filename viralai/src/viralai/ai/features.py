"""
Feature engineering for the AI Engine.

Turns a Mutation (Phase 2) plus optional context (evolutionary entropy/frequency, protein
classification) into a fixed-order numeric feature vector. Fixed, named column order is
what makes both the model and its SHAP explanations interpretable — "feature 3 mattered
most" is meaningless without a stable mapping back to what feature 3 is.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viralai.core.idm import Mutation, MutationType, ProteinMutation, ProteinMutationClass

FEATURE_NAMES: list[str] = [
    "position_normalized",
    "is_substitution",
    "is_insertion",
    "is_deletion",
    "confidence_score",
    "entropy_at_position",
    "population_frequency",
    "affects_protein",
    "is_synonymous",
    "is_missense",
    "is_nonsense",
    "is_frameshift",
]


@dataclass
class FeatureContext:
    """Optional context a caller may not always have available (e.g. entropy requires a
    population of aligned sequences; protein classification requires the Protein Engine
    to have already run). Missing context defaults to a neutral value (0.0 / None) rather
    than raising — a model should degrade gracefully with partial information, the way a
    researcher's own judgment would.
    """

    genome_length: int
    entropy_at_position: float = 0.0
    population_frequency: float = 0.0
    protein_mutation: ProteinMutation | None = None


def extract_features(mutation: Mutation, context: FeatureContext) -> dict[str, float]:
    """Build the named feature dict for one Mutation. Use `to_vector` to convert a batch
    of these into the numpy array a model actually consumes.
    """
    protein_class = context.protein_mutation.classification if context.protein_mutation else None

    return {
        "position_normalized": mutation.position / max(context.genome_length, 1),
        "is_substitution": float(mutation.mutation_type == MutationType.SUBSTITUTION),
        "is_insertion": float(mutation.mutation_type == MutationType.INSERTION),
        "is_deletion": float(mutation.mutation_type == MutationType.DELETION),
        "confidence_score": mutation.confidence_score,
        "entropy_at_position": context.entropy_at_position,
        "population_frequency": context.population_frequency,
        "affects_protein": float(context.protein_mutation is not None),
        "is_synonymous": float(protein_class == ProteinMutationClass.SYNONYMOUS),
        "is_missense": float(protein_class == ProteinMutationClass.MISSENSE),
        "is_nonsense": float(protein_class == ProteinMutationClass.NONSENSE),
        "is_frameshift": float(protein_class == ProteinMutationClass.FRAMESHIFT),
    }


def to_vector(feature_dicts: list[dict[str, float]]) -> np.ndarray:
    """Convert a batch of `extract_features` outputs into a 2D array in FEATURE_NAMES
    order. Raises KeyError early (via dict access) if a caller hands in a feature dict
    missing an expected key, rather than silently producing a misaligned row.
    """
    return np.array([[row[name] for name in FEATURE_NAMES] for row in feature_dicts], dtype=float)
