"""
Environmental Simulator (Blueprint Ch.27.3 -- listed there as a future component;
included now per project scope decision to build declared-future capabilities in the
initial implementation rather than deferring them).

Models external selective pressure (e.g. antiviral drug exposure, host immune pressure)
as a per-position fitness multiplier: an individual whose base at a given position
differs from the reference gets that position's multiplier applied to its fitness.
Multiplier > 1.0 models a resistance/escape mutation being favored under pressure;
multiplier < 1.0 models a mutation being disfavored (e.g. a fitness cost in the absence
of the pressure that would otherwise select for it).

This is a deliberately simple multiplicative model (independent per-position effects, no
epistasis) -- adequate for illustrating selective sweeps at known resistance positions
(e.g. HIV protease inhibitor resistance sites, Ch.10), not a claim of mechanistic
accuracy for any specific real mutation's fitness effect. Any position_effects values
used for a real research question should come from cited literature (the same citation
discipline as Phase 1 plugin gene coordinates), not be invented.
"""

from __future__ import annotations

import numpy as np

from viralai.common.errors import ValidationError


class EnvironmentalPressure:
    """A named, reusable selective pressure definition: which reference positions matter,
    and what fitness multiplier applies when an individual differs from the reference at
    that position.
    """

    def __init__(
        self, name: str, reference: np.ndarray, position_effects: dict[int, float]
    ) -> None:
        if any(pos < 0 or pos >= len(reference) for pos in position_effects):
            raise ValidationError(
                "position_effects contains a position outside the reference genome's "
                f"range [0, {len(reference) - 1}]"
            )
        if any(effect < 0 for effect in position_effects.values()):
            raise ValidationError("Fitness multipliers in position_effects must be non-negative")

        self.name = name
        self._reference = reference
        self._position_effects = position_effects

    def fitness_function(self, population: np.ndarray) -> np.ndarray:
        """Return one fitness value per individual in `population`
        (shape: (population_size, genome_length)).
        """
        fitness = np.ones(len(population), dtype=float)
        for position, effect in self._position_effects.items():
            differs_from_reference = population[:, position] != self._reference[position]
            fitness[differs_from_reference] *= effect
        return fitness

    def describe(self) -> str:
        clauses = [
            f"position {pos}: x{effect:.2f}"
            for pos, effect in sorted(self._position_effects.items())
        ]
        return (
            f"{self.name} ({', '.join(clauses)})"
            if clauses
            else f"{self.name} (no effects defined)"
        )
