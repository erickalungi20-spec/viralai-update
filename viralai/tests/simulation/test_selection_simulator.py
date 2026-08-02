import numpy as np
import pytest

from viralai.common.errors import ValidationError
from viralai.simulation.selection_simulator import (
    PopulationExtinctError,
    neutral_fitness,
    select_next_generation,
)


def test_neutral_fitness_is_uniform():
    population = np.zeros((5, 3), dtype=np.uint8)
    fitness = neutral_fitness(population)
    assert np.all(fitness == 1.0)


def test_select_next_generation_preserves_population_size():
    population = np.arange(20).reshape(10, 2)
    fitness = np.ones(10)
    rng = np.random.default_rng(0)

    next_gen = select_next_generation(population, fitness, rng)

    assert next_gen.shape == population.shape


def test_zero_fitness_individual_never_selected():
    population = np.array([[0, 0], [1, 1], [2, 2]])
    fitness = np.array([1.0, 0.0, 0.0])  # only individual 0 can reproduce
    rng = np.random.default_rng(0)

    next_gen = select_next_generation(population, fitness, rng)

    assert np.all(next_gen == [0, 0])


def test_all_zero_fitness_raises_population_extinct_error():
    population = np.array([[0, 0], [1, 1]])
    fitness = np.array([0.0, 0.0])
    rng = np.random.default_rng(0)

    with pytest.raises(PopulationExtinctError):
        select_next_generation(population, fitness, rng)


def test_mismatched_lengths_raises():
    population = np.zeros((5, 2))
    fitness = np.ones(3)
    rng = np.random.default_rng(0)

    with pytest.raises(ValidationError):
        select_next_generation(population, fitness, rng)


def test_negative_fitness_raises():
    population = np.zeros((3, 2))
    fitness = np.array([1.0, -1.0, 1.0])
    rng = np.random.default_rng(0)

    with pytest.raises(ValidationError):
        select_next_generation(population, fitness, rng)


def test_same_seed_produces_identical_selection():
    population = np.arange(40).reshape(20, 2)
    fitness = np.random.default_rng(1).random(20) + 0.1  # all positive

    result_a = select_next_generation(population, fitness, np.random.default_rng(99))
    result_b = select_next_generation(population, fitness, np.random.default_rng(99))

    np.testing.assert_array_equal(result_a, result_b)
