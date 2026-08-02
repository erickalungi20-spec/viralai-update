"""
Report Builder.

Assembles an AnalysisReport from the raw outputs of earlier phases (Mutation/Protein
engine results, Evolution Engine summaries, AI ReasoningRecords, Simulation experiments)
rather than each phase knowing how to render itself -- keeps the engines focused on
analysis and puts report assembly in exactly one place.
"""

from __future__ import annotations

from viralai.ai.reasoning import ReasoningRecord
from viralai.core.idm import Mutation, ProteinMutation
from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.reporting.report_models import (
    AnalysisReport,
    EvolutionReportSection,
    MutationReportEntry,
    ReportProvenance,
    SimulationReportSection,
)
from viralai.simulation.laboratory import SimulationExperiment


class ReportBuilder:
    def __init__(self, provenance: ReportProvenance, title: str) -> None:
        self._report = AnalysisReport(title=title, provenance=provenance)

    def add_mutations(
        self,
        mutations: list[Mutation],
        *,
        protein_mutations: list[ProteinMutation] | None = None,
        reasoning_by_position: dict[int, ReasoningRecord] | None = None,
    ) -> ReportBuilder:
        """Merge Mutation, ProteinMutation, and (optional) AI ReasoningRecord data into
        one row per mutation, keyed by genomic position. A mutation with no matching
        protein classification or AI reasoning simply leaves those fields None/empty --
        reports should reflect what was actually computed, not force every row into the
        same shape.
        """
        protein_by_position = {}
        if protein_mutations:
            for pm in protein_mutations:
                protein_by_position[pm.source_mutation.position] = pm

        for mutation in mutations:
            protein_mutation = protein_by_position.get(mutation.position)
            reasoning = (reasoning_by_position or {}).get(mutation.position)

            entry = MutationReportEntry(
                position=mutation.position,
                reference_base=mutation.reference_base,
                observed_base=mutation.observed_base,
                mutation_type=mutation.mutation_type.value,
                confidence_score=mutation.confidence_score,
                protein_classification=(
                    protein_mutation.classification.value if protein_mutation else None
                ),
                affected_protein=protein_mutation.protein_id if protein_mutation else None,
                reference_aa=protein_mutation.reference_aa if protein_mutation else None,
                observed_aa=protein_mutation.observed_aa if protein_mutation else None,
                literature_citations=reasoning.literature_citations if reasoning else [],
                ai_flagged_as_hotspot=reasoning.ai_prediction_positive if reasoning else None,
                ai_confidence=reasoning.ai_confidence if reasoning else None,
                cds_name=mutation.supporting_evidence.get("cds_name"),
                cds_position=mutation.supporting_evidence.get("cds_position"),
                gene_feature=mutation.supporting_evidence.get("gene_feature"),
                gene_feature_type=mutation.supporting_evidence.get("gene_feature_type"),
                supporting_evidence=mutation.supporting_evidence,
            )
            self._report.mutations.append(entry)
        return self

    def add_evolution_summary(
        self,
        evolution_engine: EvolutionAnalysisEngine,
        aligned_population: list[str],
        *,
        hotspot_threshold: float = 0.1,
    ) -> ReportBuilder:
        diversity = evolution_engine.nucleotide_diversity(aligned_population)
        entropies = evolution_engine.shannon_entropy_per_position(aligned_population)
        mean_entropy = sum(entropies) / len(entropies) if entropies else 0.0

        self._report.evolution = EvolutionReportSection(
            population_size=len(aligned_population),
            nucleotide_diversity=diversity,
            mean_entropy=mean_entropy,
            hotspot_positions=[i for i, e in enumerate(entropies) if e >= hotspot_threshold],
        )
        return self

    def add_simulation_experiment(self, experiment: SimulationExperiment) -> ReportBuilder:
        final_summary = (
            experiment.generation_summaries[-1] if experiment.generation_summaries else None
        )
        self._report.simulations.append(
            SimulationReportSection(
                experiment_name=experiment.name,
                experiment_version=experiment.version,
                is_synthetic=experiment.is_synthetic,
                generations_run=len(experiment.generation_summaries),
                extinction_generation=experiment.extinction_generation,
                final_mean_mutations_from_reference=(
                    final_summary["mean_mutations_from_reference"] if final_summary else None
                ),
                notes=experiment.notes,
            )
        )
        return self

    def set_summary_notes(self, notes: str) -> ReportBuilder:
        self._report.summary_notes = notes
        return self

    def build(self) -> AnalysisReport:
        return self._report
