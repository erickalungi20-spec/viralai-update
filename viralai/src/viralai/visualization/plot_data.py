"""
Visualization data preparation (Blueprint Ch.28).

These functions shape analysis output into plot-ready structures. They deliberately do
not depend on matplotlib -- separating "what should be plotted" from "how it gets
rendered" means the same data works for a static PNG (figures.py), a future interactive
dashboard (Phase 8+), or a Jupyter notebook's own plotting, without this module caring
which one is consuming it.
"""

from __future__ import annotations

from dataclasses import dataclass

from viralai.core.idm import Mutation


@dataclass
class GenomeMapData:
    """Data for a genome-wide mutation map (Ch.28.3 Genome Viewer): one point per
    mutation, position on the x-axis, confidence on the y-axis.
    """

    genome_length: int
    positions: list[int]
    confidence_scores: list[float]
    mutation_types: list[str]


@dataclass
class DiversityTrendData:
    """Data for an evolution dashboard trend line (Ch.28.3 Evolution Dashboard):
    nucleotide diversity and mean mutation count per generation, from a simulation.
    """

    generations: list[int]
    nucleotide_diversity: list[float]
    mean_mutations_from_reference: list[float]


@dataclass
class FeatureImportanceData:
    """Data for an AI dashboard chart (Ch.28.3 AI Dashboard): feature names and their
    contribution magnitude for one prediction (from ShapExplainer.top_features) or
    globally (from MutationHotspotModel.feature_importances).
    """

    feature_names: list[str]
    values: list[float]


def genome_map_from_mutations(mutations: list[Mutation], genome_length: int) -> GenomeMapData:
    return GenomeMapData(
        genome_length=genome_length,
        positions=[m.position for m in mutations],
        confidence_scores=[m.confidence_score for m in mutations],
        mutation_types=[m.mutation_type.value for m in mutations],
    )


def diversity_trend_from_generation_summaries(
    generation_summaries: list[dict],
) -> DiversityTrendData:
    return DiversityTrendData(
        generations=[s["generation"] for s in generation_summaries],
        nucleotide_diversity=[s["nucleotide_diversity"] for s in generation_summaries],
        mean_mutations_from_reference=[
            s["mean_mutations_from_reference"] for s in generation_summaries
        ],
    )


def feature_importance_from_dict(importances: dict[str, float]) -> FeatureImportanceData:
    names = list(importances.keys())
    values = [importances[name] for name in names]
    return FeatureImportanceData(feature_names=names, values=values)
