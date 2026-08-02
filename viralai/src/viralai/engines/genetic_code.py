"""
The standard (universal) genetic code.

This table is textbook-standard molecular biology, not virus-specific data, so unlike
plugin reference genomes it needs no per-entry citation — it's the same 64-codon table in
every genetics reference. Virus-specific reading frame *positions* (which come from plugin
gene annotations) are what still require citation; this module just implements the
universal codon -> amino acid mapping.
"""

from __future__ import annotations

from viralai.common.errors import ValidationError
from viralai.core.cache import scientific_cache

STOP_CODON_SYMBOL = "*"

STANDARD_GENETIC_CODE: dict[str, str] = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "TAT": "Y",
    "TAC": "Y",
    "TAA": STOP_CODON_SYMBOL,
    "TAG": STOP_CODON_SYMBOL,
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "TGT": "C",
    "TGC": "C",
    "TGA": STOP_CODON_SYMBOL,
    "TGG": "W",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}


@scientific_cache
def translate(nucleotide_sequence: str, *, stop_at_stop_codon: bool = True) -> str:
    """Translate a DNA sequence (assumed to start at position 1 of the reading frame)
    into a single-letter amino acid sequence.

    RNA (U instead of T) is normalized to T before translation. Any trailing 1-2
    nucleotides that don't complete a codon are silently dropped, matching standard
    translation tool behavior.

    If `stop_at_stop_codon` is True (default), translation halts at the first stop codon
    and the stop is not included in the output. If False, stop codons are represented as
    '*' and translation continues (useful for detecting premature/nonsense mutations,
    where you want to see where the stop landed relative to the reference).
    """
    sequence = nucleotide_sequence.upper().replace("U", "T")
    amino_acids: list[str] = []

    for i in range(0, len(sequence) - len(sequence) % 3, 3):
        codon = sequence[i : i + 3]
        amino_acid = STANDARD_GENETIC_CODE.get(codon)
        if amino_acid is None:
            raise ValidationError(
                f"Cannot translate codon '{codon}' at position {i}: not a valid codon"
            )
        if amino_acid == STOP_CODON_SYMBOL:
            if stop_at_stop_codon:
                break
            amino_acids.append(amino_acid)
            continue
        amino_acids.append(amino_acid)

    return "".join(amino_acids)
