"""
Mutation Simulator (Blueprint Ch.27.3).

Implements the Jukes-Cantor model (Jukes & Cantor, 1969): the simplest standard
nucleotide substitution model, where every site mutates independently at the same rate,
and a mutation is equally likely to become any of the other three bases. This is
foundational, textbook population-genetics methodology — like the standard genetic code
table in Phase 2, it needs no per-use citation the way a virus-specific gene coordinate
does, because it's the same universal model in every population genetics reference, not a
virus-specific empirical claim.

More realistic substitution models (transition/transversion bias — Kimura 1980; among-site
rate variation — gamma-distributed rates) are documented, honest future extensions, not
implemented here — see ADR-008.
"""

from __future__ import annotations

import numpy as np

from viralai.simulation.encoding import BASES


def mutate_population(
    population: np.ndarray, mutation_rate: float, rng: np.random.Generator
) -> np.ndarray:
    """Apply independent per-site Jukes-Cantor mutation to every individual in
    `population` (shape: (population_size, genome_length), uint8 base-index encoding).

    Returns a new array; the input is not modified in place, so a caller retains the
    pre-mutation population if needed (e.g. for diffing).
    """
    if not (0.0 <= mutation_rate <= 1.0):
        raise ValueError(f"mutation_rate must be in [0, 1], got {mutation_rate}")

    mutated = population.copy()
    mutate_mask = rng.random(population.shape) < mutation_rate
    num_mutations = int(mutate_mask.sum())
    if num_mutations == 0:
        return mutated

    # Jukes-Cantor: new base is uniformly one of the OTHER three bases. Adding a random
    # offset in {1, 2, 3} modulo 4 to the current base index guarantees the result always
    # differs from the original, with each of the three alternatives equally likely.
    offsets = rng.integers(1, len(BASES), size=num_mutations, dtype=np.uint8)
    mutated[mutate_mask] = (mutated[mutate_mask] + offsets) % len(BASES)
    return mutated
