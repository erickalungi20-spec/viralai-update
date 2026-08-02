"""
Internal Data Model (IDM).

Every analytical engine in ViralAI reads and writes these object types. Standardizing on
one shared model (rather than each engine inventing its own) is what makes engines
composable, testable in isolation, and safe to swap out later — see Blueprint Ch.29.

All objects here are virus-agnostic: nothing in this module knows what HPV or HIV is.
Virus-specific biology is supplied by plugins (Phase 1), never hardcoded here.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MutationType(str, Enum):
    """Blueprint Ch.7.4 — the mutation classes ViralAI must recognize."""

    SUBSTITUTION = "substitution"
    INSERTION = "insertion"
    DELETION = "deletion"
    FRAMESHIFT = "frameshift"
    COMPLEX = "complex"


class ProteinMutationClass(str, Enum):
    """Blueprint Ch.24.4 — functional classification of a protein-level change."""

    SYNONYMOUS = "synonymous"
    MISSENSE = "missense"
    NONSENSE = "nonsense"
    FRAMESHIFT = "frameshift"
    IN_FRAME_INSERTION = "in_frame_insertion"
    IN_FRAME_DELETION = "in_frame_deletion"


class EvidenceLevel(str, Enum):
    """Blueprint Ch.18.5 — how much trust a downstream consumer should place in a claim."""

    LEVEL_I_EXPERIMENTAL = "I"  # Experimentally confirmed
    LEVEL_II_MULTI_STUDY = "II"  # Supported by multiple independent studies
    LEVEL_III_LIMITED = "III"  # Supported by limited published evidence
    LEVEL_IV_COMPUTATIONAL = "IV"  # Computational prediction
    LEVEL_V_HYPOTHESIS = "V"  # Hypothesis requiring validation


class GenomeKind(str, Enum):
    """The nucleic-acid type of a viral genome."""

    DNA = "dna"
    RNA = "rna"


class GenomeStrandedness(str, Enum):
    """Physical strandedness of the genomic nucleic acid."""

    SINGLE_STRANDED = "single_stranded"
    DOUBLE_STRANDED = "double_stranded"


class GenomeTopology(str, Enum):
    """Genome organization pattern described in the reference material."""

    LINEAR = "linear"
    CIRCULAR = "circular"
    SEGMENTED = "segmented"
    MULTIPARTITE = "multipartite"


class CDSRegion(BaseModel):
    """A coding sequence region annotated on a viral genome."""

    name: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @property
    def span(self) -> tuple[int, int]:
        return (self.start, self.end)


class GeneFeature(BaseModel):
    """A gene-like feature such as an ORF, gene, or regulatory element."""

    name: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    feature_type: str = "gene"


class Genome(BaseModel):
    """A single genomic sequence under analysis, including viral genome metadata."""

    genome_id: str
    virus_species: str
    reference_version: str | None = None
    sequence: str
    genome_kind: GenomeKind = GenomeKind.DNA
    strandedness: GenomeStrandedness = GenomeStrandedness.DOUBLE_STRANDED
    topology: GenomeTopology = GenomeTopology.LINEAR
    segment_count: int | None = None
    segments: list[str] = Field(default_factory=list)
    cds_regions: list[CDSRegion] = Field(default_factory=list)
    gene_features: list[GeneFeature] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_segmented(self) -> bool:
        return self.topology in {GenomeTopology.SEGMENTED, GenomeTopology.MULTIPARTITE}

    @field_validator("sequence")
    @classmethod
    def sequence_is_nonempty_and_valid_alphabet(cls, value: str) -> str:
        if not value:
            raise ValueError("Genome.sequence must not be empty")
        allowed = set("ACGTUNRYSWKMBDHV-acgtunryswkmbdhv")
        bad_chars = set(value) - allowed
        if bad_chars:
            raise ValueError(
                f"Genome.sequence contains characters outside the IUPAC nucleotide "
                f"alphabet: {sorted(bad_chars)}"
            )
        return value

    @field_validator("segments")
    @classmethod
    def validate_segments(cls, value: list[str]) -> list[str]:
        if value:
            for segment in value:
                if not segment:
                    raise ValueError("Genome.segments must not contain empty strings")
        return value


class Mutation(BaseModel):
    """A single detected genomic change, positioned against a reference genome."""

    position: int = Field(ge=0)
    reference_base: str
    observed_base: str
    mutation_type: MutationType
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_IV_COMPUTATIONAL
    gene_annotation: str | None = None
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)


class Protein(BaseModel):
    """A translated protein and the mutations that affect it."""

    protein_id: str
    amino_acid_sequence: str
    functional_domains: list[str] = Field(default_factory=list)
    associated_mutations: list[Mutation] = Field(default_factory=list)


class ProteinMutation(BaseModel):
    """The protein-level interpretation of a genomic Mutation."""

    source_mutation: Mutation
    protein_id: str
    position_aa: int = Field(ge=0)
    reference_aa: str
    observed_aa: str
    classification: ProteinMutationClass
    affected_domain: str | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_IV_COMPUTATIONAL

    @property
    def is_synonymous(self) -> bool:
        return self.classification == ProteinMutationClass.SYNONYMOUS


class Variant(BaseModel):
    """A named collection of co-occurring mutations that define a lineage/variant."""

    variant_id: str
    characteristic_mutations: list[Mutation] = Field(default_factory=list)
    population_frequency: float | None = Field(default=None, ge=0.0, le=1.0)
    lineage_information: dict[str, Any] = Field(default_factory=dict)


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Analysis(BaseModel):
    """The record of one executed analytical workflow — the unit Provenance tracks."""

    analysis_id: str
    workflow_name: str
    status: AnalysisStatus = AnalysisStatus.PENDING
    configuration: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
