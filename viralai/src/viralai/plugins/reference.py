"""
Reference genome loading and validation.

Scientific integrity rule for this project: reference genome sequences are never
hardcoded into plugin source code or fabricated by a code-generation pass. A plugin
declares an *expected* accession, length, and checksum in its manifest/config, and this
module loads the actual FASTA from a file the developer has obtained from a verifiable
source (typically NCBI) and validates it against those expectations before anything
downstream is allowed to treat it as ground truth. If the file is missing, this fails
loudly with instructions, rather than silently substituting placeholder data.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger

logger = get_logger("plugins.reference")


@dataclass(frozen=True)
class ReferenceGenomeSpec:
    """What a plugin *expects* its reference FASTA to look like, declared up front so a
    corrupted, truncated, or wrong-virus file is caught immediately rather than producing
    silently wrong mutation coordinates later.
    """

    accession: str
    expected_length: int
    sha256: str | None = None  # optional until the plugin author has pinned a checksum


class ReferenceGenomeNotFoundError(ValidationError):
    """Raised when a plugin's reference FASTA file has not been provisioned locally."""


def load_reference_genome(fasta_path: Path | str, spec: ReferenceGenomeSpec) -> str:
    """Load and validate a reference genome FASTA against `spec`.

    Returns the raw nucleotide sequence (whitespace/header stripped, uppercased).
    Raises ReferenceGenomeNotFoundError if the file doesn't exist, and ValidationError if
    it exists but doesn't match the declared length or checksum.
    """
    path = Path(fasta_path)
    if not path.exists():
        raise ReferenceGenomeNotFoundError(
            f"Reference genome file not found at {path}. Expected accession "
            f"'{spec.accession}'. This repository does not ship real reference sequences "
            f"in source control — fetch it yourself (see the plugin's "
            f"data/reference/README.md for instructions) and place it at this path."
        )

    sequence = _parse_fasta_single_record(path)

    if len(sequence) != spec.expected_length:
        raise ValidationError(
            f"Reference genome at {path} has length {len(sequence)}, expected "
            f"{spec.expected_length} for accession '{spec.accession}'. Refusing to use it "
            f"— check you downloaded the correct accession/version."
        )

    if spec.sha256:
        actual = hashlib.sha256(sequence.encode("ascii")).hexdigest()
        if actual != spec.sha256:
            raise ValidationError(
                f"Reference genome at {path} does not match the expected SHA-256 checksum "
                f"for accession '{spec.accession}' (expected {spec.sha256}, got {actual}). "
                f"Refusing to use it — the file may be corrupted or the wrong version."
            )

    logger.info("reference genome validated: accession=%s length=%d", spec.accession, len(sequence))
    return sequence


def _parse_fasta_single_record(path: Path) -> str:
    """Minimal single-record FASTA parser. Deliberately does not depend on Biopython for
    Phase 1 — revisit if plugins start needing multi-record FASTA or richer format support.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    seq_lines = [line.strip() for line in lines if line and not line.startswith(">")]
    if not seq_lines:
        raise ValidationError(f"No sequence data found in FASTA file at {path}")
    return "".join(seq_lines).upper()
