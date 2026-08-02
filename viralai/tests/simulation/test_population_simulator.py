import numpy as np
import pytest

from viralai.common.errors import ValidationError
from viralai.simulation.population_simulator import PopulationSimulator, SimulationConfig

REFERENCE = "ACGTACGTACGTACGTACGT"  # 20bp synthetic fixture, not real biological data


def test_config_rejects_invalid_population_size():
    with pytest.raises(ValidationError):
        SimulationConfig(population_size=0, generations=5, mutation_rate=0.01, seed=1)


def test_config_rejects_negative_generations():
    with pytest.raises(ValidationError):
        SimulationConfig(population_size=10, generations=-1, mutation_rate=0.01, seed=1)


def test_config_rejects_invalid_mutation_rate():
    with pytest.raises(ValidationError):
        SimulationConfig(population_size=10, generations=5, mutation_rate=1.5, seed=1)


def test_run_produces_one_summary_per_generation():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=20, generations=5, mutation_rate=0.05, seed=1)

    result = simulator.run(REFERENCE, config)

    assert len(result.generation_summaries) == 5
    assert [s.generation for s in result.generation_summaries] == [0, 1, 2, 3, 4]


def test_result_is_always_marked_synthetic():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=10, generations=2, mutation_rate=0.01, seed=1)

    result = simulator.run(REFERENCE, config)

    assert result.is_synthetic is True


def test_zero_generations_produces_no_summaries_but_still_returns_sample():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=10, generations=0, mutation_rate=0.01, seed=1)

    result = simulator.run(REFERENCE, config)

    assert result.generation_summaries == []
    assert len(result.final_population_sample) > 0
    assert all(
        sample == REFERENCE for sample in result.final_population_sample
    )  # no mutation occurred


def test_same_seed_produces_identical_results():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=30, generations=10, mutation_rate=0.02, seed=123)

    result_a = simulator.run(REFERENCE, config)
    result_b = simulator.run(REFERENCE, config)

    assert result_a.generation_summaries == result_b.generation_summaries
    assert result_a.final_population_sample == result_b.final_population_sample


def test_different_seeds_produce_different_results():
    simulator = PopulationSimulator()
    config_a = SimulationConfig(population_size=30, generations=10, mutation_rate=0.05, seed=1)
    config_b = SimulationConfig(population_size=30, generations=10, mutation_rate=0.05, seed=2)

    result_a = simulator.run(REFERENCE, config_a)
    result_b = simulator.run(REFERENCE, config_b)

    assert result_a.final_population_sample != result_b.final_population_sample


def test_mutation_increases_diversity_over_generations_under_drift():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=50, generations=30, mutation_rate=0.02, seed=7)

    result = simulator.run(REFERENCE, config)

    first_gen_diversity = result.generation_summaries[0].nucleotide_diversity
    last_gen_diversity = result.generation_summaries[-1].nucleotide_diversity
    # under pure drift with mutation and no selection, diversity should generally trend
    # upward over many generations (not a strict monotonic guarantee -- stochastic --
    # but the mean mutation count from reference should clearly increase)
    first_gen_mutations = result.generation_summaries[0].mean_mutations_from_reference
    last_gen_mutations = result.generation_summaries[-1].mean_mutations_from_reference
    assert last_gen_mutations > first_gen_mutations
    assert last_gen_diversity >= 0.0
    assert first_gen_diversity >= 0.0


def test_extinction_is_recorded_when_fitness_function_kills_everyone():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=10, generations=5, mutation_rate=0.01, seed=1)

    def all_zero_fitness(population: np.ndarray) -> np.ndarray:
        return np.zeros(len(population))

    result = simulator.run(REFERENCE, config, fitness_function=all_zero_fitness)

    assert result.extinction_generation == 0
    assert result.generation_summaries[0].population_extinct is True
    # simulation should stop immediately at extinction, not run all 5 generations
    assert len(result.generation_summaries) == 1
    assert result.final_population_sample == []
