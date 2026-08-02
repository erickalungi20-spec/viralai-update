from viralai.core.idm import Mutation, MutationType
from viralai.visualization.plot_data import (
    diversity_trend_from_generation_summaries,
    feature_importance_from_dict,
    genome_map_from_mutations,
)


def test_genome_map_from_mutations():
    mutations = [
        Mutation(
            position=10,
            reference_base="A",
            observed_base="T",
            mutation_type=MutationType.SUBSTITUTION,
            confidence_score=0.9,
        ),
        Mutation(
            position=20,
            reference_base="C",
            observed_base="G",
            mutation_type=MutationType.SUBSTITUTION,
            confidence_score=0.7,
        ),
    ]

    data = genome_map_from_mutations(mutations, genome_length=1000)

    assert data.genome_length == 1000
    assert data.positions == [10, 20]
    assert data.confidence_scores == [0.9, 0.7]
    assert data.mutation_types == ["substitution", "substitution"]


def test_diversity_trend_from_generation_summaries():
    summaries = [
        {"generation": 0, "nucleotide_diversity": 0.0, "mean_mutations_from_reference": 0.1},
        {"generation": 1, "nucleotide_diversity": 0.05, "mean_mutations_from_reference": 0.3},
    ]

    data = diversity_trend_from_generation_summaries(summaries)

    assert data.generations == [0, 1]
    assert data.nucleotide_diversity == [0.0, 0.05]
    assert data.mean_mutations_from_reference == [0.1, 0.3]


def test_feature_importance_from_dict_preserves_order():
    importances = {"position_normalized": 0.4, "confidence_score": 0.3, "is_missense": 0.3}

    data = feature_importance_from_dict(importances)

    assert data.feature_names == ["position_normalized", "confidence_score", "is_missense"]
    assert data.values == [0.4, 0.3, 0.3]
