"""
Report data models (Blueprint Ch.19.3 Report Structure, Ch.19.6 Scientific Traceability).

An AnalysisReport is the single structured object every exporter (Markdown/JSON/CSV/HTML)
renders from -- build the report once, export it many ways, rather than each export
format re-deriving its own view of the analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from viralai.core.idm import EvidenceLevel


class ReportProvenance(BaseModel):
    """Blueprint Ch.19.6: every report must record software version, workflow version,
    plugin version, reference genome, parameters, and execution timestamp -- the same
    fields Phase 0's Metadata/Provenance managers already track, surfaced here so a
    report is self-describing without the reader needing separate access to the system
    that produced it.
    """

    software_version: str
    virus: str
    reference_genome_accession: str | None = None
    plugin_name: str | None = None
    plugin_version: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MutationReportEntry(BaseModel):
    position: int
    reference_base: str
    observed_base: str
    mutation_type: str
    confidence_score: float
    protein_classification: str | None = None
    affected_protein: str | None = None
    reference_aa: str | None = None
    observed_aa: str | None = None
    literature_citations: list[str] = Field(default_factory=list)
    ai_flagged_as_hotspot: bool | None = None
    ai_confidence: float | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_IV_COMPUTATIONAL
    cds_name: str | None = None
    cds_position: int | None = None
    gene_feature: str | None = None
    gene_feature_type: str | None = None
    supporting_evidence: dict[str, object] = Field(default_factory=dict)


class EvolutionReportSection(BaseModel):
    population_size: int
    nucleotide_diversity: float
    mean_entropy: float
    hotspot_positions: list[int] = Field(default_factory=list)


class SimulationReportSection(BaseModel):
    experiment_name: str
    experiment_version: str
    is_synthetic: bool = True
    generations_run: int
    extinction_generation: int | None
    final_mean_mutations_from_reference: float | None
    notes: str = ""


class AnalysisReport(BaseModel):
    """The top-level report object. Every field beyond `provenance` is optional because a
    report might cover only mutation detection, or might span all five phases -- callers
    build up only the sections they actually have data for.
    """

    title: str
    provenance: ReportProvenance
    mutations: list[MutationReportEntry] = Field(default_factory=list)
    evolution: EvolutionReportSection | None = None
    simulations: list[SimulationReportSection] = Field(default_factory=list)
    summary_notes: str = ""

    @property
    def is_research_use_disclaimer_required(self) -> bool:
        """True if this report contains any AI-derived or simulated content -- Ch.36
        requires those to always carry a research-use disclaimer. A report of purely
        deterministic mutation detection with no AI/simulation content technically
        doesn't need one, but exporters apply it unconditionally anyway (see
        exporters.py) since a partially-populated report can gain AI/simulation content
        later and it's safer to never omit the disclaimer than to compute this exactly.
        """
        return any(m.ai_flagged_as_hotspot is not None for m in self.mutations) or bool(
            self.simulations
        )
