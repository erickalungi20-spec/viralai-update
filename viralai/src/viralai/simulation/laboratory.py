"""
Digital Laboratory Manager (engineering review Recommendation 6; Blueprint Ch.13.5,
Ch.27).

Wraps the Population Simulator with an experiment registry: every simulation run is
stored as a named, versioned SimulationExperiment with its full configuration (including
the random seed -- Ch.27.6 reproducibility), so a researcher works in terms of
"experiments" they can list, compare, and replay, not one-off script runs whose exact
parameters are lost the moment the terminal closes.

Same file-backed, versioned-directory pattern as Phase 4's ModelRegistry -- deliberately
consistent with that precedent rather than inventing a new storage convention.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from viralai.common.errors import ValidationError
from viralai.common.ids import new_id
from viralai.common.logging import get_logger
from viralai.simulation.population_simulator import (
    FitnessFunction,
    GenerationSummary,
    PopulationSimulator,
    SimulationConfig,
    SimulationResult,
)

logger = get_logger("simulation.laboratory")


class SimulationExperiment(BaseModel):
    """The persisted record of one simulation run -- everything needed to understand,
    reproduce, or compare it later without re-reading the code that produced it.
    """

    experiment_id: str
    name: str
    version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    config: dict
    reference_genome_length: int
    generation_summaries: list[dict]
    final_population_sample: list[str]
    is_synthetic: bool = True
    extinction_generation: int | None = None
    notes: str = ""


class DigitalLaboratoryManager:
    """Runs simulations via PopulationSimulator and persists them as named, versioned
    SimulationExperiment records. `storage_dir` follows the same layout convention as
    Phase 4's ModelRegistry: one subdirectory per (name, version).
    """

    def __init__(self, storage_dir: Path | str) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._simulator = PopulationSimulator()

    def run_experiment(
        self,
        *,
        name: str,
        version: str,
        reference_genome: str,
        config: SimulationConfig,
        fitness_function: FitnessFunction | None = None,
        notes: str = "",
    ) -> SimulationExperiment:
        experiment_dir = self._experiment_dir(name, version)
        if experiment_dir.exists():
            raise ValidationError(f"Experiment '{name}' version '{version}' already exists")

        result = self._simulator.run(reference_genome, config, fitness_function=fitness_function)
        experiment = _result_to_experiment(name, version, result, notes)

        experiment_dir.mkdir(parents=True)
        (experiment_dir / "experiment.json").write_text(
            experiment.model_dump_json(indent=2), encoding="utf-8"
        )
        logger.info("experiment stored: %s v%s (%d generations)", name, version, config.generations)
        return experiment

    def get_experiment(self, name: str, version: str) -> SimulationExperiment:
        path = self._experiment_dir(name, version) / "experiment.json"
        if not path.exists():
            raise ValidationError(f"No experiment '{name}' version '{version}'")
        return SimulationExperiment(**json.loads(path.read_text(encoding="utf-8")))

    def list_versions(self, name: str) -> list[str]:
        name_dir = self._storage_dir / _safe(name)
        if not name_dir.exists():
            return []
        return sorted(p.name for p in name_dir.iterdir() if p.is_dir())

    def replay(
        self,
        name: str,
        version: str,
        reference_genome: str,
        *,
        fitness_function: FitnessFunction | None = None,
    ) -> SimulationExperiment:
        """Re-run a stored experiment's exact configuration (including its seed) and
        return the new result as an unregistered SimulationExperiment (not persisted --
        replay is for verification, not for creating a duplicate registry entry).

        Because Wright-Fisher + Jukes-Cantor with a fixed seed is fully deterministic,
        `replay(...).generation_summaries` should exactly equal the original's -- that
        equality IS the reproducibility guarantee Ch.27.6 requires, made checkable rather
        than just asserted in documentation.
        """
        original = self.get_experiment(name, version)
        config = SimulationConfig(**original.config)
        result = self._simulator.run(reference_genome, config, fitness_function=fitness_function)
        return _result_to_experiment(
            name, f"{version}-replay", result, notes="replay verification run"
        )

    def compare(self, name: str, version_a: str, version_b: str) -> dict:
        """A small diff between two experiments' final-generation summary statistics --
        the kind of quick comparison a researcher reaches for when asking "did the drug
        pressure scenario actually behave differently from the neutral baseline".
        """
        exp_a = self.get_experiment(name, version_a)
        exp_b = self.get_experiment(name, version_b)

        final_a = exp_a.generation_summaries[-1] if exp_a.generation_summaries else {}
        final_b = exp_b.generation_summaries[-1] if exp_b.generation_summaries else {}

        return {
            "version_a": version_a,
            "version_b": version_b,
            "final_diversity_a": final_a.get("nucleotide_diversity"),
            "final_diversity_b": final_b.get("nucleotide_diversity"),
            "final_mean_mutations_a": final_a.get("mean_mutations_from_reference"),
            "final_mean_mutations_b": final_b.get("mean_mutations_from_reference"),
            "extinction_a": exp_a.extinction_generation,
            "extinction_b": exp_b.extinction_generation,
        }

    def _experiment_dir(self, name: str, version: str) -> Path:
        return self._storage_dir / _safe(name) / _safe(version)


def _result_to_experiment(
    name: str, version: str, result: SimulationResult, notes: str
) -> SimulationExperiment:
    return SimulationExperiment(
        experiment_id=new_id("experiment"),
        name=name,
        version=version,
        config=result.config.__dict__,
        reference_genome_length=result.reference_genome_length,
        generation_summaries=[_summary_to_dict(s) for s in result.generation_summaries],
        final_population_sample=result.final_population_sample,
        is_synthetic=result.is_synthetic,
        extinction_generation=result.extinction_generation,
        notes=notes,
    )


def _summary_to_dict(summary: GenerationSummary) -> dict:
    return {
        "generation": summary.generation,
        "nucleotide_diversity": summary.nucleotide_diversity,
        "mean_mutations_from_reference": summary.mean_mutations_from_reference,
        "population_extinct": summary.population_extinct,
    }


def _safe(value: str) -> str:
    if not value or "/" in value or "\\" in value or ".." in value:
        raise ValidationError(f"Invalid experiment name/version identifier: {value!r}")
    return value
