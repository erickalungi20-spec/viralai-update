"""
Mutation Analysis Engine (Blueprint Ch.23).

Compares a query genome against a reference genome and produces a list of standardized
Mutation IDM objects. This is the first engine in the pipeline — everything downstream
(Protein Engine, Evolution Engine, AI Engine) consumes its output, so its correctness
matters more than its cleverness. See ADR-005 for the alignment strategy this relies on.
"""

from __future__ import annotations

from viralai.core.event_bus import EventBus
from viralai.core.idm import (
    CDSRegion,
    GeneFeature,
    Genome,
    GenomeKind,
    GenomeStrandedness,
    GenomeTopology,
    Mutation,
    MutationType,
    ProteinMutation,
    ProteinMutationClass,
)
from viralai.engines.alignment import GAP, needleman_wunsch

MUTATION_DETECTED_TOPIC = "mutation.detected"
MUTATION_ANALYSIS_COMPLETE_TOPIC = "mutation.analysis_complete"


class MutationEngine:
    _CODON_TABLE = {
        "TTT": "F",
        "TTC": "F",
        "TTA": "L",
        "TTG": "L",
        "TCT": "S",
        "TCC": "S",
        "TCA": "S",
        "TCG": "S",
        "TAT": "Y",
        "TAC": "Y",
        "TAA": "*",
        "TAG": "*",
        "TGT": "C",
        "TGC": "C",
        "TGA": "*",
        "TGG": "W",
        "CTT": "L",
        "CTC": "L",
        "CTA": "L",
        "CTG": "L",
        "CCT": "P",
        "CCC": "P",
        "CCA": "P",
        "CCG": "P",
        "CAT": "H",
        "CAC": "H",
        "CAA": "Q",
        "CAG": "Q",
        "CGT": "R",
        "CGC": "R",
        "CGA": "R",
        "CGG": "R",
        "ATT": "I",
        "ATC": "I",
        "ATA": "I",
        "ATG": "M",
        "ACT": "T",
        "ACC": "T",
        "ACA": "T",
        "ACG": "T",
        "AAT": "N",
        "AAC": "N",
        "AAA": "K",
        "AAG": "K",
        "AGT": "S",
        "AGC": "S",
        "AGA": "R",
        "AGG": "R",
        "GTT": "V",
        "GTC": "V",
        "GTA": "V",
        "GTG": "V",
        "GCT": "A",
        "GCC": "A",
        "GCA": "A",
        "GCG": "A",
        "GAT": "D",
        "GAC": "D",
        "GAA": "E",
        "GAG": "E",
        "GGT": "G",
        "GGC": "G",
        "GGA": "G",
        "GGG": "G",
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus

    def detect_mutations(
        self,
        reference: str | Genome,
        query: str | Genome,
        *,
        source: str | None = None,
        reverse_complement: bool = False,
        genome_kind: GenomeKind | None = None,
        strandedness: GenomeStrandedness | None = None,
        topology: GenomeTopology | None = None,
    ) -> list[Mutation]:
        """Compare `query` against `reference` and return detected Mutations.

        Supports both plain strings and Genome objects. If genomes are provided, the
        engine also records their viral-genome metadata in the mutation evidence.
        """
        reference_genome = self._coerce_genome(reference)
        query_genome = self._coerce_genome(query)

        if genome_kind is not None:
            reference_genome.genome_kind = genome_kind
            query_genome.genome_kind = genome_kind
        if strandedness is not None:
            reference_genome.strandedness = strandedness
            query_genome.strandedness = strandedness
        if topology is not None:
            reference_genome.topology = topology
            query_genome.topology = topology

        if reference_genome.is_segmented or query_genome.is_segmented:
            mutations = self._compare_segmented_genomes(reference_genome, query_genome)
        else:
            reference_sequence = reference_genome.sequence
            query_sequence = query_genome.sequence
            if reverse_complement:
                query_sequence = self._reverse_complement(query_sequence)
            if len(reference_sequence) == len(query_sequence):
                mutations = self._compare_equal_length(reference_sequence, query_sequence)
            else:
                alignment = needleman_wunsch(reference_sequence, query_sequence)
                mutations = self._compare_aligned(
                    alignment.aligned_reference, alignment.aligned_query
                )

        for mutation in mutations:
            mutation.supporting_evidence.setdefault("genome_kind", reference_genome.genome_kind.value)
            mutation.supporting_evidence.setdefault("strandedness", reference_genome.strandedness.value)
            mutation.supporting_evidence.setdefault("topology", reference_genome.topology.value)
            mutation.supporting_evidence.setdefault("nucleic_acid_kind", reference_genome.genome_kind.value)
            mutation.supporting_evidence.setdefault(
                "reverse_complement_applied", reverse_complement
            )
            cds_context = self._find_cds_context(reference_genome, mutation.position)
            if cds_context is not None:
                mutation.supporting_evidence["cds_name"] = cds_context.name
                mutation.supporting_evidence["cds_position"] = mutation.position - cds_context.start

            gene_context = self._find_gene_feature(reference_genome, mutation.position)
            if gene_context is not None:
                mutation.supporting_evidence["gene_feature"] = gene_context.name
                mutation.supporting_evidence["gene_feature_type"] = gene_context.feature_type

        if self.event_bus is not None:
            for mutation in mutations:
                self.event_bus.publish(
                    MUTATION_DETECTED_TOPIC,
                    {"mutation": mutation.model_dump(mode="json")},
                    source=source or "mutation_engine",
                )
            self.event_bus.publish(
                MUTATION_ANALYSIS_COMPLETE_TOPIC,
                {"mutation_count": len(mutations)},
                source=source or "mutation_engine",
            )

        return mutations

    def translate_to_protein_mutations(self, reference: str | Genome, query: str | Genome) -> list[ProteinMutation]:
        """Translate a reference/query pair into protein-level mutations."""
        reference_genome = self._coerce_genome(reference)
        query_genome = self._coerce_genome(query)

        reference_sequence = reference_genome.sequence
        query_sequence = query_genome.sequence

        if len(reference_sequence) != len(query_sequence):
            return []

        protein_mutations: list[ProteinMutation] = []
        for cds_region in reference_genome.cds_regions:
            ref_segment = reference_sequence[cds_region.start : cds_region.end + 1]
            query_segment = query_sequence[cds_region.start : cds_region.end + 1]
            if len(ref_segment) < 3 or len(query_segment) < 3:
                continue

            reference_protein = self._translate_sequence(ref_segment)
            query_protein = self._translate_sequence(query_segment)
            for index, (ref_aa, query_aa) in enumerate(zip(reference_protein, query_protein)):
                if ref_aa == query_aa:
                    continue
                mutation = Mutation(
                    position=cds_region.start + (index * 3),
                    reference_base=ref_segment[index * 3 : index * 3 + 3],
                    observed_base=query_segment[index * 3 : index * 3 + 3],
                    mutation_type=MutationType.SUBSTITUTION,
                    confidence_score=0.9,
                )
                classification = (
                    ProteinMutationClass.SYNONYMOUS
                    if ref_aa == query_aa
                    else ProteinMutationClass.MISSENSE
                )
                protein_mutations.append(
                    ProteinMutation(
                        source_mutation=mutation,
                        protein_id=cds_region.name,
                        position_aa=index,
                        reference_aa=ref_aa,
                        observed_aa=query_aa,
                        classification=classification,
                    )
                )
        return protein_mutations

    @staticmethod
    def _coerce_genome(value: str | Genome) -> Genome:
        if isinstance(value, Genome):
            return value
        return Genome(genome_id="inline", virus_species="unknown", sequence=value)

    @staticmethod
    def _translate_sequence(sequence: str) -> str:
        if len(sequence) % 3 != 0:
            sequence = sequence[: len(sequence) // 3 * 3]
        amino_acids: list[str] = []
        for index in range(0, len(sequence), 3):
            codon = sequence[index : index + 3].upper()
            amino_acids.append(MutationEngine._CODON_TABLE.get(codon, "X"))
        return "".join(amino_acids)

    @staticmethod
    def _find_cds_context(genome: Genome, position: int) -> CDSRegion | None:
        for region in genome.cds_regions:
            if region.start <= position <= region.end:
                return region
        for region in genome.cds_regions:
            if position == region.end + 1:
                return region
        return None

    @staticmethod
    def _find_gene_feature(genome: Genome, position: int) -> GeneFeature | None:
        for feature in genome.gene_features:
            if feature.start <= position <= feature.end:
                return feature
        for feature in genome.gene_features:
            if position == feature.end + 1:
                return feature
        return None

    @staticmethod
    def _reverse_complement(sequence: str) -> str:
        complement_map = {
            "A": "T",
            "T": "A",
            "C": "G",
            "G": "C",
            "U": "A",
            "R": "Y",
            "Y": "R",
            "K": "M",
            "M": "K",
            "S": "S",
            "W": "W",
            "B": "V",
            "D": "H",
            "H": "D",
            "V": "B",
            "N": "N",
            "a": "t",
            "t": "a",
            "c": "g",
            "g": "c",
            "u": "a",
            "r": "y",
            "y": "r",
            "k": "m",
            "m": "k",
            "s": "s",
            "w": "w",
            "b": "v",
            "d": "h",
            "h": "d",
            "v": "b",
            "n": "n",
        }
        return "".join(complement_map.get(base, base) for base in reversed(sequence))

    @staticmethod
    def _compare_segmented_genomes(reference: Genome, query: Genome) -> list[Mutation]:
        reference_segments = reference.segments or [reference.sequence]
        query_segments = query.segments or [query.sequence]

        if len(reference_segments) != len(query_segments):
            reference_segments = reference_segments[: min(len(reference_segments), len(query_segments))]
            query_segments = query_segments[: min(len(reference_segments), len(query_segments))]

        mutations: list[Mutation] = []
        for index, (ref_segment, query_segment) in enumerate(zip(reference_segments, query_segments)):
            if len(ref_segment) == len(query_segment):
                segment_mutations = MutationEngine._compare_equal_length(ref_segment, query_segment)
            else:
                alignment = needleman_wunsch(ref_segment, query_segment)
                segment_mutations = MutationEngine._compare_aligned(
                    alignment.aligned_reference, alignment.aligned_query
                )

            for mutation in segment_mutations:
                mutation.supporting_evidence["segment_index"] = index
                mutations.append(mutation)
        return mutations

    @staticmethod
    def _compare_equal_length(reference: str, query: str) -> list[Mutation]:
        mutations: list[Mutation] = []
        for position, (ref_base, obs_base) in enumerate(zip(reference, query)):
            if ref_base != obs_base:
                mutations.append(
                    Mutation(
                        position=position,
                        reference_base=ref_base,
                        observed_base=obs_base,
                        mutation_type=MutationType.SUBSTITUTION,
                        confidence_score=1.0,
                    )
                )
        return mutations

    @staticmethod
    def _compare_aligned(aligned_reference: str, aligned_query: str) -> list[Mutation]:
        """Walk a gapped alignment and emit Mutations. Position is tracked in reference
        coordinates (gaps in the reference don't advance the position counter, matching
        how insertions are conventionally reported relative to a reference genome).

        Adjacent gap columns are coalesced into one indel event. A three-base deletion,
        for example, is scientifically one deletion with ``reference_base`` length three,
        not three unrelated single-base frameshifts. That preserves the information the
        Protein Engine needs to distinguish in-frame indels from frameshifts.
        """
        mutations: list[Mutation] = []
        ref_position = 0
        alignment_index = 0

        while alignment_index < len(aligned_reference):
            ref_char = aligned_reference[alignment_index]
            query_char = aligned_query[alignment_index]
            if ref_char == GAP:
                # Insertion relative to the reference. Consume the whole contiguous run
                # so an in-frame insertion stays a single, correctly sized event.
                inserted: list[str] = []
                while (
                    alignment_index < len(aligned_reference)
                    and aligned_reference[alignment_index] == GAP
                ):
                    inserted.append(aligned_query[alignment_index])
                    alignment_index += 1
                mutations.append(
                    Mutation(
                        position=ref_position,
                        reference_base="",
                        observed_base="".join(inserted),
                        mutation_type=MutationType.INSERTION,
                        confidence_score=0.9,  # alignment-derived, slightly lower default confidence
                    )
                )
                continue

            if query_char == GAP:
                # Deletion relative to the reference. As above, coalesce a contiguous
                # run instead of emitting a misleading frameshift per base.
                deleted: list[str] = []
                while (
                    alignment_index < len(aligned_reference)
                    and aligned_query[alignment_index] == GAP
                ):
                    deleted.append(aligned_reference[alignment_index])
                    alignment_index += 1
                mutations.append(
                    Mutation(
                        position=ref_position,
                        reference_base="".join(deleted),
                        observed_base="",
                        mutation_type=MutationType.DELETION,
                        confidence_score=0.9,
                    )
                )
                ref_position += len(deleted)
                continue

            if ref_char != query_char:
                mutations.append(
                    Mutation(
                        position=ref_position,
                        reference_base=ref_char,
                        observed_base=query_char,
                        mutation_type=MutationType.SUBSTITUTION,
                        confidence_score=0.9,
                    )
                )
            ref_position += 1
            alignment_index += 1

        return mutations
