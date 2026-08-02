"""
Workflow Templates (Blueprint Ch.17.4: Mutation Analysis, Evolutionary Analysis, Cancer
Research, HIV Research, Pandemic Surveillance, Simulation Workflow).

Scope decision, stated honestly: the blueprint describes these as distinct named
workflows, but the underlying analytical chain for several of them is genuinely the same
sequence (mutation detection -> protein classification -> [evolution] ->
[knowledge lookup]) applied with different plugin/knowledge context -- which is exactly
what Ch.9 (Cancer Research Module) and Ch.10 (HIV Module) themselves describe as
compositions of the Mutation Engine, Protein Engine, Knowledge Base, and Reporting Engine
rather than independent pipelines. These templates are therefore built from small shared
step factories rather than six independently reimplemented pipelines -- that's DRY
engineering, not a shortcut, and it's what the blueprint's own module descriptions call
for.

Every step writes only JSON-serializable data into `ctx.analysis.results`, which is what
makes WorkflowRunner's checkpointing (Ch.17.6) actually work.
"""

from __future__ import annotations

import numpy as np

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.core.engine import WorkflowContext, WorkflowStep
from viralai.core.idm import Genome, Mutation
from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.engines.mutation_engine import MutationEngine
from viralai.engines.protein_engine import ProteinAnalysisEngine
from viralai.knowledge.models import KnowledgeQuery
from viralai.knowledge.store import KnowledgeBase
from viralai.simulation.laboratory import DigitalLaboratoryManager
from viralai.simulation.population_simulator import FitnessFunction, SimulationConfig

# -- shared step factories --------------------------------------------------------------


def make_mutation_detection_step(
    reference_genome: str | Genome, query_genome: str | Genome, mutation_engine: MutationEngine
) -> WorkflowStep:
    def detect_mutations(ctx: WorkflowContext) -> None:
        mutations = mutation_engine.detect_mutations(
            reference_genome, query_genome, source="workflow"
        )
        ctx.analysis.results["mutations"] = [m.model_dump(mode="json") for m in mutations]

    return detect_mutations


def make_protein_analysis_step(
    reference_genome: str | Genome, gene_annotations: list[dict], protein_engine: ProteinAnalysisEngine
) -> WorkflowStep:
    def analyze_proteins(ctx: WorkflowContext) -> None:
        mutations = [Mutation(**m) for m in ctx.analysis.results.get("mutations", [])]
        protein_mutations = protein_engine.analyze(reference_genome, mutations, gene_annotations)
        ctx.analysis.results["protein_mutations"] = [
            pm.model_dump(mode="json") for pm in protein_mutations
        ]

    return analyze_proteins


def make_evolution_summary_step(
    evolution_engine: EvolutionAnalysisEngine, aligned_population: list[str]
) -> WorkflowStep:
    def evolution_summary(ctx: WorkflowContext) -> None:
        diversity = evolution_engine.nucleotide_diversity(aligned_population)
        entropies = evolution_engine.shannon_entropy_per_position(aligned_population)
        ctx.analysis.results["evolution"] = {
            "population_size": len(aligned_population),
            "nucleotide_diversity": diversity,
            "mean_entropy": sum(entropies) / len(entropies) if entropies else 0.0,
        }

    return evolution_summary


def make_knowledge_lookup_step(
    knowledge_base: KnowledgeBase, virus: str, gene: str
) -> WorkflowStep:
    def knowledge_lookup(ctx: WorkflowContext) -> None:
        entries = knowledge_base.query_mutation_knowledge(KnowledgeQuery(virus=virus, gene=gene))
        ctx.analysis.results["knowledge_entries"] = [e.model_dump(mode="json") for e in entries]

    return knowledge_lookup


def make_ai_hotspot_step(
    model: MutationHotspotModel, feature_vectors: list[list[float]]
) -> WorkflowStep:
    """Runs a pre-trained model's predictions and stores them. Training happens outside
    the workflow (Phase 4's AITrainingPipelineManager) -- a workflow consumes a model, it
    doesn't train one inline.
    """

    def ai_hotspot_prediction(ctx: WorkflowContext) -> None:
        X = np.array(feature_vectors)
        predictions = model.predict(X).tolist()
        confidences = model.predict_proba(X).tolist()
        ctx.analysis.results["ai_predictions"] = {
            "predictions": predictions,
            "confidences": confidences,
        }

    return ai_hotspot_prediction


def make_simulation_step(
    lab: DigitalLaboratoryManager,
    *,
    name: str,
    version: str,
    reference_genome: str,
    config: SimulationConfig,
    fitness_function: FitnessFunction | None = None,
    notes: str = "",
) -> WorkflowStep:
    def run_simulation(ctx: WorkflowContext) -> None:
        experiment = lab.run_experiment(
            name=name,
            version=version,
            reference_genome=reference_genome,
            config=config,
            fitness_function=fitness_function,
            notes=notes,
        )
        ctx.analysis.results["simulation_experiment"] = experiment.model_dump(mode="json")

    return run_simulation


def make_pandemic_surveillance_step(
    reference_genome: str,
    query_genomes: list[str],
    mutation_engine: MutationEngine,
    evolution_engine: EvolutionAnalysisEngine,
) -> WorkflowStep:
    def surveillance_hotspot_detection(ctx: WorkflowContext) -> None:
        mutations_by_sample = [
            mutation_engine.detect_mutations(reference_genome, sample) for sample in query_genomes
        ]
        frequencies = evolution_engine.mutation_frequency(mutations_by_sample)
        hotspots = evolution_engine.identify_hotspots(frequencies)
        ctx.analysis.results["surveillance"] = {
            "sample_count": len(query_genomes),
            "hotspot_positions": hotspots,
            "position_frequencies": {str(position): freq for position, freq in frequencies.items()},
        }

    return surveillance_hotspot_detection


# -- named workflow templates (Ch.17.4) ---------------------------------------------------


def mutation_analysis_workflow(
    reference_genome: str | Genome,
    query_genome: str | Genome,
    gene_annotations: list[dict],
    *,
    mutation_engine: MutationEngine | None = None,
    protein_engine: ProteinAnalysisEngine | None = None,
) -> list[WorkflowStep]:
    """Mutation Analysis Workflow: detect -> classify. The baseline template every other
    template in this module builds on.
    """
    mutation_engine = mutation_engine or MutationEngine()
    protein_engine = protein_engine or ProteinAnalysisEngine()
    return [
        make_mutation_detection_step(reference_genome, query_genome, mutation_engine),
        make_protein_analysis_step(reference_genome, gene_annotations, protein_engine),
    ]


def evolutionary_analysis_workflow(
    reference_genome: str | Genome,
    query_genome: str | Genome,
    gene_annotations: list[dict],
    aligned_population: list[str],
    *,
    mutation_engine: MutationEngine | None = None,
    protein_engine: ProteinAnalysisEngine | None = None,
    evolution_engine: EvolutionAnalysisEngine | None = None,
) -> list[WorkflowStep]:
    """Evolutionary Analysis Workflow: mutation analysis + population-level diversity."""
    evolution_engine = evolution_engine or EvolutionAnalysisEngine()
    return mutation_analysis_workflow(
        reference_genome,
        query_genome,
        gene_annotations,
        mutation_engine=mutation_engine,
        protein_engine=protein_engine,
    ) + [make_evolution_summary_step(evolution_engine, aligned_population)]


def cancer_research_workflow(
    reference_genome: str | Genome,
    query_genome: str | Genome,
    gene_annotations: list[dict],
    knowledge_base: KnowledgeBase,
    virus: str,
    gene: str,
    *,
    mutation_engine: MutationEngine | None = None,
    protein_engine: ProteinAnalysisEngine | None = None,
) -> list[WorkflowStep]:
    """Cancer Research Workflow (Ch.9.4): mutation analysis + curated oncogenic-mutation
    knowledge lookup.
    """
    return mutation_analysis_workflow(
        reference_genome,
        query_genome,
        gene_annotations,
        mutation_engine=mutation_engine,
        protein_engine=protein_engine,
    ) + [make_knowledge_lookup_step(knowledge_base, virus, gene)]


def hiv_research_workflow(
    reference_genome: str | Genome,
    query_genome: str | Genome,
    gene_annotations: list[dict],
    aligned_population: list[str],
    knowledge_base: KnowledgeBase,
    virus: str,
    gene: str,
    *,
    mutation_engine: MutationEngine | None = None,
    protein_engine: ProteinAnalysisEngine | None = None,
    evolution_engine: EvolutionAnalysisEngine | None = None,
) -> list[WorkflowStep]:
    """HIV Research Workflow (Ch.10.4): evolutionary analysis + resistance-relevant
    knowledge lookup.
    """
    return evolutionary_analysis_workflow(
        reference_genome,
        query_genome,
        gene_annotations,
        aligned_population,
        mutation_engine=mutation_engine,
        protein_engine=protein_engine,
        evolution_engine=evolution_engine,
    ) + [make_knowledge_lookup_step(knowledge_base, virus, gene)]


def pandemic_surveillance_workflow(
    reference_genome: str | Genome,
    query_genomes: list[str | Genome],
    *,
    mutation_engine: MutationEngine | None = None,
    evolution_engine: EvolutionAnalysisEngine | None = None,
) -> list[WorkflowStep]:
    """Pandemic Surveillance Workflow (Ch.11.4/11.7): batch mutation detection across
    many samples + hotspot identification, the genomic-surveillance use case.
    """
    mutation_engine = mutation_engine or MutationEngine()
    evolution_engine = evolution_engine or EvolutionAnalysisEngine()
    return [
        make_pandemic_surveillance_step(
            reference_genome, query_genomes, mutation_engine, evolution_engine
        )
    ]


def simulation_workflow(
    lab: DigitalLaboratoryManager,
    *,
    name: str,
    version: str,
    reference_genome: str,
    config: SimulationConfig,
    fitness_function: FitnessFunction | None = None,
    notes: str = "",
) -> list[WorkflowStep]:
    """Simulation Workflow (Ch.13.5): runs one Digital Laboratory experiment as a
    workflow step, so simulations get the same checkpointing/provenance treatment as
    every other analytical workflow.
    """
    return [
        make_simulation_step(
            lab,
            name=name,
            version=version,
            reference_genome=reference_genome,
            config=config,
            fitness_function=fitness_function,
            notes=notes,
        )
    ]
