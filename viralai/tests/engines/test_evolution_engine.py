import pytest

from viralai.common.errors import ValidationError
from viralai.core.idm import Mutation, MutationType
from viralai.engines.evolution_engine import EvolutionAnalysisEngine


def test_shannon_entropy_zero_for_fully_conserved_column():
    engine = EvolutionAnalysisEngine()
    entropies = engine.shannon_entropy_per_position(["AAAA", "AAAA", "AAAA"])
    assert entropies == [0.0, 0.0, 0.0, 0.0]


def test_shannon_entropy_maximal_for_evenly_split_column():
    engine = EvolutionAnalysisEngine()
    # position 0: A,A,C,C -- 50/50 split -> entropy of 1 bit
    entropies = engine.shannon_entropy_per_position(["AT", "AT", "CT", "CT"])
    assert entropies[0] == pytest.approx(1.0)
    assert entropies[1] == pytest.approx(0.0)  # T is fully conserved


def test_shannon_entropy_requires_equal_length_sequences():
    engine = EvolutionAnalysisEngine()
    with pytest.raises(ValidationError):
        engine.shannon_entropy_per_position(["AAAA", "AA"])


def test_nucleotide_diversity_zero_for_identical_population():
    engine = EvolutionAnalysisEngine()
    diversity = engine.nucleotide_diversity(["ACGT", "ACGT", "ACGT"])
    assert diversity == 0.0


def test_nucleotide_diversity_single_sequence_is_zero():
    engine = EvolutionAnalysisEngine()
    assert engine.nucleotide_diversity(["ACGT"]) == 0.0


def test_nucleotide_diversity_reflects_pairwise_differences():
    engine = EvolutionAnalysisEngine()
    # two sequences differing at 1 of 4 positions -> pi = 0.25
    diversity = engine.nucleotide_diversity(["ACGT", "ACGA"])
    assert diversity == pytest.approx(0.25)


def test_mutation_frequency_counts_fraction_of_samples():
    engine = EvolutionAnalysisEngine()
    sample1 = [
        Mutation(
            position=10,
            reference_base="A",
            observed_base="G",
            mutation_type=MutationType.SUBSTITUTION,
        )
    ]
    sample2 = [
        Mutation(
            position=10,
            reference_base="A",
            observed_base="G",
            mutation_type=MutationType.SUBSTITUTION,
        )
    ]
    sample3: list[Mutation] = []  # no mutation at position 10

    frequencies = engine.mutation_frequency([sample1, sample2, sample3])

    assert frequencies[10] == pytest.approx(2 / 3)


def test_mutation_frequency_empty_input_returns_empty_dict():
    engine = EvolutionAnalysisEngine()
    assert engine.mutation_frequency([]) == {}


def test_identify_hotspots_filters_and_sorts_by_frequency():
    engine = EvolutionAnalysisEngine()
    frequencies = {10: 0.5, 20: 0.05, 30: 0.9}

    hotspots = engine.identify_hotspots(frequencies, threshold=0.1)

    assert hotspots == [30, 10]  # above threshold, sorted descending; position 20 excluded
