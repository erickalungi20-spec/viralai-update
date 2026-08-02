"""
Selection Simulator (Blueprint Ch.27.3).

Implements Wright-Fisher reproduction (Fisher 1930, Wright 1931): the next generation is
sampled with replacement from the current one, with each individual's probability of being
a parent proportional to its fitness. Fitness == 1.0 for everyone reduces to pure genetic
drift (neutral evolution) -- that's the default when no fitness function is supplied.
"""

from __future__ import annotations

import numpy as np

from viralai.common.errors import ValidationError


class PopulationExtinctError(ValidationError):
    """Raised when every individual in a population has zero fitness -- Wright-Fisher
    sampling cannot proceed because there is nothing left to weight by. This is a real,
    meaningful simulation outcome (total population collapse under selective pressure),
    not just an edge case to paper over.
    """


def select_next_generation(
    population: np.ndarray, fitness_values: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Sample a new population of the same size, with replacement, weighted by fitness.

    `fitness_values` must be non-negative and have one entry per individual in
    `population`. If every individual has zero fitness, raises PopulationExtinctError
    rather than silently doing uniform sampling (which would misrepresent an extinction
    event as neutral drift).
    """
    if len(fitness_values) != len(population):
        raise ValidationError(
            f"fitness_values has {len(fitness_values)} entries but population has "
            f"{len(population)} individuals"
        )
    if np.any(fitness_values < 0):
        raise ValidationError("fitness_values must be non-negative")

    total_fitness = fitness_values.sum()
    if total_fitness <= 0:
        raise PopulationExtinctError(
            "Total population fitness is zero -- every individual has zero fitness. "
            "This represents total population collapse under the current selective "
            "pressure, not a computational error."
        )

    probabilities = fitness_values / total_fitness
    indices = rng.choice(len(population), size=len(population), replace=True, p=probabilities)
    return population[indices]


def neutral_fitness(population: np.ndarray) -> np.ndarray:
    """The default fitness function: every individual has fitness 1.0 (pure genetic
    drift, no selection). Use this explicitly when you want drift-only dynamics rather
    than relying on a None-means-neutral convention elsewhere in the codebase.
    """
    return np.ones(len(population), dtype=float)
