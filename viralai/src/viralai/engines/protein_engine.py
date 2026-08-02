"""
Protein Analysis Engine (Blueprint Ch.24).

Translates gene regions using a plugin's gene annotations and interprets each genomic
Mutation (from the Mutation Engine) as a protein-level change: synonymous, missense,
nonsense, or frameshift.

Scope limitation, stated honestly rather than hidden: single-nucleotide insertions/
deletions are always classified as FRAMESHIFT here. A true in-frame indel requires
recognizing that several adjacent single-base indels together total a multiple of 3 bases
(Blueprint Ch.23.5's "Complex Mutations" concept) — that merging step is not implemented
in Phase 2. This means a genuinely in-frame multi-base indel will currently be reported as
several individual frameshift events rather than one in-frame event. Documented in
ADR-005 as a known gap, not a silent inaccuracy.
"""

from __future__ import annotations

from viralai.core.idm import Genome, Mutation, MutationType, ProteinMutation, ProteinMutationClass
from viralai.engines.genetic_code import STOP_CODON_SYMBOL, translate

# Standard amino acid physicochemical groupings (textbook classification, not
# virus-specific — used only for a coarse conservative/radical substitution heuristic).
_AMINO_ACID_GROUPS: dict[str, str] = {
    # nonpolar / hydrophobic
    "A": "nonpolar",
    "V": "nonpolar",
    "L": "nonpolar",
    "I": "nonpolar",
    "M": "nonpolar",
    "P": "nonpolar",
    "G": "nonpolar",
    "W": "nonpolar",
    "F": "nonpolar",
    # polar uncharged
    "S": "polar",
    "T": "polar",
    "C": "polar",
    "Y": "polar",
    "N": "polar",
    "Q": "polar",
    # acidic
    "D": "acidic",
    "E": "acidic",
    # basic
    "K": "basic",
    "R": "basic",
    "H": "basic",
}


class ProteinAnalysisEngine:
    """Interprets Mutation objects within a gene's coordinates as protein-level changes."""

    def analyze(
        self,
        reference_genome: str | Genome,
        mutations: list[Mutation],
        gene_annotations: list[dict],
    ) -> list[ProteinMutation]:
        """Classify every mutation that falls within a gene's declared coordinates.

        `gene_annotations` entries use 1-based inclusive coordinates (matching the
        Plugin Development Standard's convention, e.g. E6: start=104, end=559).
        Mutations outside every declared gene are skipped — they may be in the LCR
        or another non-coding/unannotated region.
        """
        reference_sequence = self._coerce_sequence(reference_genome)

        results: list[ProteinMutation] = []
        for gene in gene_annotations:
            gene_start_0based = gene["start"] - 1
            gene_end_0based = gene["end"] - 1
            gene_name = gene["gene"]
            ref_gene_seq = reference_sequence[gene_start_0based : gene["end"]]

            for mutation in mutations:
                if not (gene_start_0based <= mutation.position <= gene_end_0based):
                    continue
                offset = mutation.position - gene_start_0based
                protein_mutation = self._classify_one(mutation, gene_name, ref_gene_seq, offset)
                if protein_mutation is not None:
                    results.append(protein_mutation)
        return results

    def translate_gene(self, reference_genome: str | Genome, gene_annotation: dict) -> str:
        """Return the reference protein sequence for one gene (stop-terminated)."""
        reference_sequence = self._coerce_sequence(reference_genome)
        gene_seq = reference_sequence[gene_annotation["start"] - 1 : gene_annotation["end"]]
        return translate(gene_seq)

    @staticmethod
    def _coerce_sequence(reference_genome: str | Genome) -> str:
        if isinstance(reference_genome, Genome):
            return reference_genome.sequence
        return reference_genome

    def _classify_one(
        self, mutation: Mutation, gene_name: str, ref_gene_seq: str, offset: int
    ) -> ProteinMutation | None:
        codon_index = offset // 3

        if mutation.mutation_type == MutationType.SUBSTITUTION:
            codon_start = codon_index * 3
            ref_codon = ref_gene_seq[codon_start : codon_start + 3]
            if len(ref_codon) < 3:
                return None  # incomplete trailing codon at the gene boundary

            position_in_codon = offset % 3
            mutated_codon = (
                ref_codon[:position_in_codon]
                + mutation.observed_base
                + ref_codon[position_in_codon + 1 :]
            )
            ref_aa = translate(ref_codon, stop_at_stop_codon=False) or STOP_CODON_SYMBOL
            mut_aa = translate(mutated_codon, stop_at_stop_codon=False) or STOP_CODON_SYMBOL

            return ProteinMutation(
                source_mutation=mutation,
                protein_id=gene_name,
                position_aa=codon_index,
                reference_aa=ref_aa,
                observed_aa=mut_aa,
                classification=_classify_substitution(ref_aa, mut_aa),
            )

        if mutation.mutation_type in (MutationType.INSERTION, MutationType.DELETION):
            indel_length = len(mutation.observed_base or mutation.reference_base)
            in_frame = indel_length > 0 and indel_length % 3 == 0
            if mutation.mutation_type == MutationType.INSERTION:
                classification = (
                    ProteinMutationClass.IN_FRAME_INSERTION
                    if in_frame
                    else ProteinMutationClass.FRAMESHIFT
                )
            else:
                classification = (
                    ProteinMutationClass.IN_FRAME_DELETION
                    if in_frame
                    else ProteinMutationClass.FRAMESHIFT
                )
            return ProteinMutation(
                source_mutation=mutation,
                protein_id=gene_name,
                position_aa=codon_index,
                reference_aa="",
                observed_aa="",
                classification=classification,
            )

        return None


def _classify_substitution(ref_aa: str, mut_aa: str) -> ProteinMutationClass:
    if ref_aa == mut_aa:
        return ProteinMutationClass.SYNONYMOUS
    if mut_aa == STOP_CODON_SYMBOL:
        return ProteinMutationClass.NONSENSE
    return ProteinMutationClass.MISSENSE


def estimate_substitution_severity(reference_aa: str, observed_aa: str) -> str:
    """Coarse conservative/radical heuristic (Blueprint Ch.24.5) based on standard amino
    acid physicochemical grouping. This is a heuristic, not a validated impact predictor —
    callers should tag results with EvidenceLevel.LEVEL_IV_COMPUTATIONAL, never higher.
    """
    if reference_aa == observed_aa:
        return "none"
    if reference_aa == STOP_CODON_SYMBOL or observed_aa == STOP_CODON_SYMBOL:
        return "radical"
    ref_group = _AMINO_ACID_GROUPS.get(reference_aa)
    obs_group = _AMINO_ACID_GROUPS.get(observed_aa)
    if ref_group is None or obs_group is None:
        return "unknown"
    return "conservative" if ref_group == obs_group else "radical"
