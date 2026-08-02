import pytest

from viralai.common.errors import ValidationError
from viralai.simulation.encoding import encode
from viralai.simulation.environmental_simulator import EnvironmentalPressure
from viralai.simulation.laboratory import DigitalLaboratoryManager
from viralai.simulation.population_simulator import SimulationConfig

REFERENCE = "ACGTACGTACGTACGTACGT"


def test_run_experiment_and_get_experiment_round_trip(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    config = SimulationConfig(population_size=20, generations=5, mutation_rate=0.02, seed=1)

    experiment = lab.run_experiment(
        name="drift-baseline",
        version="0.1.0",
        reference_genome=REFERENCE,
        config=config,
        notes="baseline drift run",
    )

    assert experiment.name == "drift-baseline"
    assert experiment.is_synthetic is True
    assert len(experiment.generation_summaries) == 5

    loaded = lab.get_experiment("drift-baseline", "0.1.0")
    assert loaded.experiment_id == experiment.experiment_id
    assert loaded.notes == "baseline drift run"


def test_duplicate_experiment_registration_raises(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    config = SimulationConfig(population_size=10, generations=2, mutation_rate=0.01, seed=1)
    lab.run_experiment(name="exp", version="0.1.0", reference_genome=REFERENCE, config=config)

    with pytest.raises(ValidationError):
        lab.run_experiment(name="exp", version="0.1.0", reference_genome=REFERENCE, config=config)


def test_get_unregistered_experiment_raises(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    with pytest.raises(ValidationError):
        lab.get_experiment("nonexistent", "0.1.0")


def test_list_versions(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    config = SimulationConfig(population_size=10, generations=2, mutation_rate=0.01, seed=1)
    lab.run_experiment(name="exp", version="0.1.0", reference_genome=REFERENCE, config=config)
    lab.run_experiment(name="exp", version="0.2.0", reference_genome=REFERENCE, config=config)

    assert set(lab.list_versions("exp")) == {"0.1.0", "0.2.0"}
    assert lab.list_versions("nonexistent") == []


def test_replay_reproduces_identical_generation_summaries(tmp_path):
    """This is the reproducibility guarantee from ADR-008 made checkable: replaying an
    experiment with its stored seed and parameters must give byte-identical results.
    """
    lab = DigitalLaboratoryManager(tmp_path)
    config = SimulationConfig(population_size=25, generations=8, mutation_rate=0.03, seed=42)
    original = lab.run_experiment(
        name="reproducibility-check", version="0.1.0", reference_genome=REFERENCE, config=config
    )

    replayed = lab.replay("reproducibility-check", "0.1.0", REFERENCE)

    assert replayed.generation_summaries == original.generation_summaries
    assert replayed.final_population_sample == original.final_population_sample


def test_replay_with_environmental_pressure_is_also_reproducible(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    reference_encoded = encode(REFERENCE)
    pressure = EnvironmentalPressure("test-pressure", reference_encoded, {0: 1.5, 5: 0.5})
    config = SimulationConfig(
        population_size=25, generations=6, mutation_rate=0.05, seed=7, pressure_name="test-pressure"
    )

    original = lab.run_experiment(
        name="pressure-check",
        version="0.1.0",
        reference_genome=REFERENCE,
        config=config,
        fitness_function=pressure.fitness_function,
        notes="under selective pressure",
    )

    replayed = lab.replay(
        "pressure-check", "0.1.0", REFERENCE, fitness_function=pressure.fitness_function
    )

    assert replayed.generation_summaries == original.generation_summaries


def test_compare_two_experiments(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    config_low = SimulationConfig(population_size=20, generations=10, mutation_rate=0.01, seed=1)
    config_high = SimulationConfig(population_size=20, generations=10, mutation_rate=0.2, seed=1)

    lab.run_experiment(
        name="mutation-rate-comparison",
        version="low",
        reference_genome=REFERENCE,
        config=config_low,
    )
    lab.run_experiment(
        name="mutation-rate-comparison",
        version="high",
        reference_genome=REFERENCE,
        config=config_high,
    )

    comparison = lab.compare("mutation-rate-comparison", "low", "high")

    assert comparison["version_a"] == "low"
    assert comparison["version_b"] == "high"
    # higher mutation rate should produce more mutations from reference by the final generation
    assert comparison["final_mean_mutations_b"] > comparison["final_mean_mutations_a"]


def test_unsafe_name_is_rejected(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path)
    config = SimulationConfig(population_size=10, generations=2, mutation_rate=0.01, seed=1)
    with pytest.raises(ValidationError):
        lab.run_experiment(
            name="../escape", version="0.1.0", reference_genome=REFERENCE, config=config
        )
