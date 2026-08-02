"""
Global sequence alignment (Needleman-Wunsch).

Design decision, documented here and in ADR-005: Phase 2's Mutation Engine needs to handle
sequences of unequal length (insertions/deletions), which requires alignment, not just
positional comparison. Rather than depend on an external bioinformatics library for one
algorithm, this is a small, correct, pure-Python implementation.

This is intentionally a *simple* aligner: linear gap penalty, no affine gap scoring, no
codon-awareness. It is adequate for gene-length sequences (hundreds to a few thousand bp)
in a research/testing context. It is O(n*m) time and space, which is the known limitation —
see ADR-005 for the plan to swap in a proper library (e.g. parasail, edlib) once whole-
genome-scale alignment performance actually matters.
"""

from __future__ import annotations

from dataclasses import dataclass

GAP = "-"


@dataclass(frozen=True)
class AlignmentResult:
    aligned_reference: str
    aligned_query: str
    score: int


def needleman_wunsch(
    reference: str,
    query: str,
    *,
    match_score: int = 1,
    mismatch_penalty: int = -1,
    gap_penalty: int = -2,
) -> AlignmentResult:
    """Global alignment of `query` against `reference`. Returns both sequences padded
    with '-' gap characters so they're the same length and directly comparable
    position-by-position.
    """
    n, m = len(reference), len(query)

    # dp[i][j] = best score aligning reference[:i] with query[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + gap_penalty
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + gap_penalty

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = dp[i - 1][j - 1] + (
                match_score if reference[i - 1] == query[j - 1] else mismatch_penalty
            )
            up = dp[i - 1][j] + gap_penalty
            left = dp[i][j - 1] + gap_penalty
            dp[i][j] = max(diag, up, left)

    # traceback
    aligned_ref: list[str] = []
    aligned_query: list[str] = []
    i, j = n, m
    while i > 0 or j > 0:
        current = dp[i][j]
        if i > 0 and j > 0:
            diag_score = dp[i - 1][j - 1] + (
                match_score if reference[i - 1] == query[j - 1] else mismatch_penalty
            )
            if current == diag_score:
                aligned_ref.append(reference[i - 1])
                aligned_query.append(query[j - 1])
                i -= 1
                j -= 1
                continue
        if i > 0 and current == dp[i - 1][j] + gap_penalty:
            aligned_ref.append(reference[i - 1])
            aligned_query.append(GAP)
            i -= 1
            continue
        aligned_ref.append(GAP)
        aligned_query.append(query[j - 1])
        j -= 1

    return AlignmentResult(
        aligned_reference="".join(reversed(aligned_ref)),
        aligned_query="".join(reversed(aligned_query)),
        score=dp[n][m],
    )
