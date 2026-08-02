import numpy as np
import pytest

from viralai.common.errors import ValidationError
from viralai.simulation.encoding import encode
from viralai.simulation.environmental_simulator import EnvironmentalPressure


def test_individuals_matching_reference_get_baseline_fitness():
    reference = encode("ACGT")
    population = np.tile(reference, (5, 1))
    pressure = EnvironmentalPressure("drug-pressure", reference, {0: 2.0})

    fitness = pressure.fitness_function(population)

    assert np.all(fitness == 1.0)  # nobody differs from reference at position 0


def test_individuals_differing_at_effect_position_get_multiplier_applied():
    reference = encode("ACGT")
    population = np.tile(reference, (3, 1))
    population[0, 0] = encode("T")[0]  # individual 0 differs from reference at position 0
    pressure = EnvironmentalPressure("drug-pressure", reference, {0: 2.5})

    fitness = pressure.fitness_function(population)

    assert fitness[0] == pytest.approx(2.5)
    assert fitness[1] == pytest.approx(1.0)
    assert fitness[2] == pytest.approx(1.0)


def test_multiple_position_effects_multiply_together():
    reference = encode("ACGT")
    population = np.tile(reference, (1, 1))
    population[0, 0] = encode("T")[0]
    population[0, 1] = encode("T")[0]
    pressure = EnvironmentalPressure("drug-pressure", reference, {0: 2.0, 1: 3.0})

    fitness = pressure.fitness_function(population)

    assert fitness[0] == pytest.approx(6.0)  # 2.0 * 3.0


def test_out_of_range_position_raises():
    reference = encode("ACGT")
    with pytest.raises(ValidationError):
        EnvironmentalPressure("bad-pressure", reference, {100: 2.0})


def test_negative_effect_raises():
    reference = encode("ACGT")
    with pytest.raises(ValidationError):
        EnvironmentalPressure("bad-pressure", reference, {0: -1.0})


def test_describe_includes_name_and_positions():
    reference = encode("ACGT")
    pressure = EnvironmentalPressure("antiviral-drug", reference, {0: 2.0, 2: 0.5})

    description = pressure.describe()

    assert "antiviral-drug" in description
    assert "position 0" in description
    assert "position 2" in description
