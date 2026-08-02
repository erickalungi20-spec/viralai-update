"""
Evolution Analysis Engine (Blueprint Ch.25).

Population-level statistics over a set of genomes or their detected mutations: Shannon
entropy per position, nucleotide diversity (pi), mutation frequency, and hotspot
identification. These are standard population genetics formulas (Nei & Li 1979 for
nucleotide diversity; Shannon 1948 for entropy) — general scientific method, not
virus-specific claims, so no per-virus citation is needed the way plugin gene coordinates
require one.

All functions here assume their input sequences are already aligned (equal length) —
this engine does not run alignment itself. Align first (Mutation Engine / alignment
module), then hand the aligned set to this engine.
"""

from __future__ import annotations

import math
from collections import Counter

from viralai.common.errors import ValidationError
from viralai.core.idm import Mutation


class EvolutionAnalysisEngine:
    def shannon_entropy_per_position(self, aligned_sequences: list[str]) -> list[float]:
        """Shannon entropy (base 2, in bits) at each alignment column.

        Low entropy = conserved position (candidate functional constraint).
        High entropy = variable position (candidate mutation hotspot / relaxed constraint).
        """
        _require_aligned(aligned_sequences)
        length = len(aligned_sequences[0])
        entropies: list[float] = []
        for position in range(length):
            column = [seq[position] for seq in aligned_sequences]
            entropies.append(_shannon_entropy(column))
        return entropies

    def nucleotide_diversity(self, aligned_sequences: list[str]) -> float:
        """Average pairwise nucleotide difference proportion across all sequence pairs
        (the pi statistic, Nei & Li 1979). Returns 0.0 for a single sequence or an empty
        population (nothing to compare).
        """
        _require_aligned(aligned_sequences)
        n = len(aligned_sequences)
        if n < 2:
            return 0.0

        length = len(aligned_sequences[0])
        total_pairwise_diff_proportion = 0.0
        pair_count = 0
        for i in range(n):
            for j in range(i + 1, n):
                differences = sum(
                    1 for a, b in zip(aligned_sequences[i], aligned_sequences[j]) if a != b
                )
                total_pairwise_diff_proportion += differences / length
                pair_count += 1

        return total_pairwise_diff_proportion / pair_count

    def mutation_frequency(self, mutations_by_sample: list[list[Mutation]]) -> dict[int, float]:
        """Fraction of samples carrying a mutation at each genomic position.

        `mutations_by_sample` is one list of Mutations per sample (e.g. the output of
        MutationEngine.detect_mutations run once per sample against the same reference).
        """
        sample_count = len(mutations_by_sample)
        if sample_count == 0:
            return {}

        position_counts: Counter[int] = Counter()
        for sample_mutations in mutations_by_sample:
            positions_in_this_sample = {m.position for m in sample_mutations}
            position_counts.update(positions_in_this_sample)

        return {position: count / sample_count for position, count in position_counts.items()}

    def identify_hotspots(
        self, frequencies: dict[int, float], *, threshold: float = 0.1
    ) -> list[int]:
        """Positions whose mutation frequency meets or exceeds `threshold`, sorted by
        descending frequency (most-mutated first).
        """
        hotspots = [position for position, freq in frequencies.items() if freq >= threshold]
        return sorted(hotspots, key=lambda p: frequencies[p], reverse=True)


def _shannon_entropy(symbols: list[str]) -> float:
    total = len(symbols)
    counts = Counter(symbols)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def _require_aligned(sequences: list[str]) -> None:
    if not sequences:
        raise ValidationError("At least one sequence is required")
    length = len(sequences[0])
    if any(len(seq) != length for seq in sequences):
        raise ValidationError(
            "All sequences must be the same length (already aligned) before analysis — "
            "run them through MutationEngine/alignment first"
        )
