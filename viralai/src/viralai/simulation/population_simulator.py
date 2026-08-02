"""
Population Simulator (Blueprint Ch.27.4 Simulation Workflow, Ch.13.4 Evolution Simulation).

Orchestrates: Reference Genome -> Simulation Parameters -> Mutation Generation ->
Population Evolution -> Selection -> Statistical Analysis, one generation at a time,
using numpy's Generator API for fully reproducible randomness (Ch.27.6 -- the random
seed IS the experiment's identity as much as its parameters are).

Scope limitation, stated honestly (see ADR-008): this tracks population-level summary
statistics (nucleotide diversity per generation) rather than full genealogical/lineage
trees. A researcher wanting "which individual descended from which" needs phylogenetic
lineage tracking, which is a real, separate feature not yet built.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger
from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.simulation.encoding import decode, encode
from viralai.simulation.mutation_simulator import mutate_population
from viralai.simulation.selection_simulator import (
    PopulationExtinctError,
    neutral_fitness,
    select_next_generation,
)

logger = get_logger("simulation.population")

FitnessFunction = Callable[[np.ndarray], np.ndarray]


@dataclass
class SimulationConfig:
    population_size: int
    generations: int
    mutation_rate: float
    seed: int
    pressure_name: str | None = (
        None  # descriptive only -- the actual fitness_function is passed separately
    )

    def __post_init__(self) -> None:
        if self.population_size <= 0:
            raise ValidationError("population_size must be positive")
        if self.generations < 0:
            raise ValidationError("generations must be non-negative")
        if not (0.0 <= self.mutation_rate <= 1.0):
            raise ValidationError("mutation_rate must be in [0, 1]")


@dataclass
class GenerationSummary:
    generation: int
    nucleotide_diversity: float
    mean_mutations_from_reference: float
    population_extinct: bool = False


@dataclass
class SimulationResult:
    config: SimulationConfig
    reference_genome_length: int
    generation_summaries: list[GenerationSummary] = field(default_factory=list)
    final_population_sample: list[str] = field(default_factory=list)
    is_synthetic: bool = True  # Ch.13.6: every simulation output is explicitly marked synthetic
    extinction_generation: int | None = None


class PopulationSimulator:
    """Runs a Wright-Fisher population simulation with Jukes-Cantor mutation, optionally
    under a supplied fitness function (e.g. from EnvironmentalPressure.fitness_function).
    """

    def __init__(self) -> None:
        self._evolution_engine = EvolutionAnalysisEngine()

    def run(
        self,
        reference_genome: str,
        config: SimulationConfig,
        *,
        fitness_function: FitnessFunction | None = None,
        sample_size_for_summary: int = 20,
        final_sample_size: int = 10,
    ) -> SimulationResult:
        rng = np.random.default_rng(config.seed)
        reference_encoded = encode(reference_genome)
        fitness_fn = fitness_function or neutral_fitness

        population = np.tile(reference_encoded, (config.population_size, 1))

        result = SimulationResult(config=config, reference_genome_length=len(reference_genome))

        for generation in range(config.generations):
            population = mutate_population(population, config.mutation_rate, rng)

            fitness_values = fitness_fn(population)
            try:
                population = select_next_generation(population, fitness_values, rng)
            except PopulationExtinctError:
                logger.warning(
                    "population extinct at generation %d under pressure '%s'",
                    generation,
                    config.pressure_name,
                )
                result.extinction_generation = generation
                result.generation_summaries.append(
                    GenerationSummary(
                        generation=generation,
                        nucleotide_diversity=0.0,
                        mean_mutations_from_reference=float(len(reference_genome)),
                        population_extinct=True,
                    )
                )
                break

            summary = self._summarize_generation(
                generation, population, reference_encoded, sample_size_for_summary, rng
            )
            result.generation_summaries.append(summary)

        # A zero-fitness generation has no surviving population. Returning the
        # pre-selection array here would contradict the extinction marker and could make
        # downstream reports treat extinct genomes as final survivors.
        result.final_population_sample = (
            []
            if result.extinction_generation is not None
            else self._sample_as_strings(population, final_sample_size, rng)
        )
        logger.info(
            "simulation complete: %d generations, pop_size=%d, seed=%d, extinct=%s",
            config.generations,
            config.population_size,
            config.seed,
            result.extinction_generation is not None,
        )
        return result

    def _summarize_generation(
        self,
        generation: int,
        population: np.ndarray,
        reference_encoded: np.ndarray,
        sample_size: int,
        rng: np.random.Generator,
    ) -> GenerationSummary:
        sample = self._sample_as_strings(population, min(sample_size, len(population)), rng)
        diversity = self._evolution_engine.nucleotide_diversity(sample) if len(sample) > 1 else 0.0

        mutation_counts = (population != reference_encoded).sum(axis=1)
        mean_mutations = float(mutation_counts.mean())

        return GenerationSummary(
            generation=generation,
            nucleotide_diversity=diversity,
            mean_mutations_from_reference=mean_mutations,
        )

    @staticmethod
    def _sample_as_strings(
        population: np.ndarray, sample_size: int, rng: np.random.Generator
    ) -> list[str]:
        sample_size = min(sample_size, len(population))
        indices = rng.choice(len(population), size=sample_size, replace=False)
        return [decode(population[i]) for i in indices]
