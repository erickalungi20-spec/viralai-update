import numpy as np
import pytest

from viralai.simulation.encoding import encode
from viralai.simulation.mutation_simulator import mutate_population


def test_zero_mutation_rate_produces_no_changes():
    population = np.tile(encode("ACGTACGT"), (10, 1))
    rng = np.random.default_rng(0)

    mutated = mutate_population(population, mutation_rate=0.0, rng=rng)

    np.testing.assert_array_equal(mutated, population)


def test_full_mutation_rate_changes_every_site():
    population = np.tile(encode("ACGTACGT"), (10, 1))
    rng = np.random.default_rng(0)

    mutated = mutate_population(population, mutation_rate=1.0, rng=rng)

    # every single site must differ from the original (Jukes-Cantor guarantees this)
    assert np.all(mutated != population)


def test_mutation_never_produces_out_of_range_base_index():
    population = np.tile(encode("ACGTACGT"), (50, 1))
    rng = np.random.default_rng(1)

    mutated = mutate_population(population, mutation_rate=1.0, rng=rng)

    assert np.all(mutated < 4)
    assert np.all(mutated >= 0)


def test_partial_mutation_rate_changes_roughly_expected_fraction():
    population = np.tile(encode("A" * 1000), (20, 1))
    rng = np.random.default_rng(2)

    mutated = mutate_population(population, mutation_rate=0.1, rng=rng)

    fraction_changed = (mutated != population).mean()
    assert 0.05 < fraction_changed < 0.15  # loose bound, avoids flakiness


def test_input_array_not_modified_in_place():
    population = np.tile(encode("ACGT"), (5, 1))
    original_copy = population.copy()
    rng = np.random.default_rng(0)

    mutate_population(population, mutation_rate=1.0, rng=rng)

    np.testing.assert_array_equal(population, original_copy)


def test_same_seed_produces_identical_mutations():
    population = np.tile(encode("ACGTACGTACGT"), (10, 1))

    result_a = mutate_population(population, mutation_rate=0.3, rng=np.random.default_rng(42))
    result_b = mutate_population(population, mutation_rate=0.3, rng=np.random.default_rng(42))

    np.testing.assert_array_equal(result_a, result_b)


def test_invalid_mutation_rate_raises():
    population = np.tile(encode("ACGT"), (5, 1))
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        mutate_population(population, mutation_rate=1.5, rng=rng)
