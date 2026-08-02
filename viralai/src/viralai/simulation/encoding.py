"""
Integer encoding for nucleotides, used throughout the simulation package for
numpy-vectorized performance. A-C-G-T only (no ambiguity codes) — simulated genomes are
synthetic constructs starting from a clean reference, not real sequencing data that might
contain IUPAC ambiguity codes.
"""

from __future__ import annotations

import numpy as np

from viralai.common.errors import ValidationError

BASES = "ACGT"
_BASE_TO_INT = {base: i for i, base in enumerate(BASES)}


def encode(sequence: str) -> np.ndarray:
    """String -> uint8 array of base indices (A=0, C=1, G=2, T=3)."""
    try:
        return np.array([_BASE_TO_INT[base] for base in sequence.upper()], dtype=np.uint8)
    except KeyError as exc:
        raise ValidationError(
            f"Cannot encode sequence for simulation: contains a non-ACGT character {exc}. "
            f"Simulated genomes must start from a clean A/C/G/T reference."
        ) from exc


def decode(encoded: np.ndarray) -> str:
    """uint8 array of base indices -> string."""
    return "".join(BASES[i] for i in encoded)
