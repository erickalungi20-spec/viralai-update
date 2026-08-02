import pytest

from viralai.benchmarking.reproducibility import assert_reproducible, check_reproducibility
from viralai.engines.mutation_engine import MutationEngine
from viralai.simulation.population_simulator import PopulationSimulator, SimulationConfig


def test_deterministic_function_is_reproducible():
    report = check_reproducibility("constant", lambda: 42)
    assert report.reproducible is True


def test_nondeterministic_function_is_not_reproducible():
    import random

    report = check_reproducibility("random", lambda: random.random())
    assert report.reproducible is False


def test_assert_reproducible_passes_silently_for_deterministic_function():
    assert_reproducible("constant", lambda: [1, 2, 3])  # should not raise


def test_assert_reproducible_raises_for_nondeterministic_function():
    import random

    with pytest.raises(AssertionError):
        assert_reproducible("random", lambda: random.random())


def test_mutation_detection_is_reproducible():
    """Real-world usage: Mutation Engine detection is a pure function of its inputs and
    should always be reproducible.
    """
    engine = MutationEngine()

    def run():
        mutations = engine.detect_mutations("ATGCAATAA", "ATGCTATAA")
        return tuple((m.position, m.reference_base, m.observed_base) for m in mutations)

    assert_reproducible("mutation_detection", run)


def test_simulation_with_fixed_seed_is_reproducible():
    """Real-world usage: the Population Simulator's determinism guarantee (ADR-008),
    checked through the same general harness used for everything else.
    """
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=10, generations=5, mutation_rate=0.05, seed=42)

    def run():
        result = simulator.run("ACGTACGTACGT", config)
        return tuple(
            (
                s.generation,
                round(s.nucleotide_diversity, 10),
                round(s.mean_mutations_from_reference, 10),
            )
            for s in result.generation_summaries
        )

    assert_reproducible("simulation_fixed_seed", run)
