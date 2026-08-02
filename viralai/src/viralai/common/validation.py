"""
Validation utilities.

Blueprint Ch.5.2.2 requires every imported dataset to be validated before analysis begins.
This module holds the primitive checks; engine-specific validation (e.g. "is this a valid
HPV genome") belongs in the relevant plugin, not here — this stays virus-agnostic.
"""

from __future__ import annotations

_NUCLEOTIDE_ALPHABET = set("ACGTUNRYSWKMBDHV-")


def is_valid_nucleotide_sequence(sequence: str) -> bool:
    """True if `sequence` contains only IUPAC nucleotide codes (case-insensitive)."""
    if not sequence:
        return False
    return set(sequence.upper()) <= _NUCLEOTIDE_ALPHABET


def is_valid_amino_acid_sequence(sequence: str) -> bool:
    """True if `sequence` contains only standard single-letter amino acid codes."""
    if not sequence:
        return False
    allowed = set("ACDEFGHIKLMNPQRSTVWY*X")
    return set(sequence.upper()) <= allowed
