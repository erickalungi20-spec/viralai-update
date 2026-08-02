"""
The capstone integration test: Phase 1 (plugin gene annotations) -> Phase 2 (Mutation +
Protein engines) -> Phase 3 (Knowledge Base + Research Graph) -> Phase 4 (AI Engine +
Scientific Reasoning Engine), all wired together against one small synthetic genome. This
is the test that proves the four phases actually compose into one working system, not
just four independently-passing test suites.
"""

from __future__ import annotations

import numpy as np

from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FEATURE_NAMES, FeatureContext, extract_features, to_vector
from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.reasoning import ScientificReasoningEngine
from viralai.core.idm import EvidenceLevel
from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.engines.mutation_engine import MutationEngine
from viralai.engines.protein_engine import ProteinAnalysisEngine
from viralai.graph.ingestion import (
    ingest_knowledge_base,
    ingest_mutations,
    ingest_protein_mutations,
    ingest_virus_and_genes,
)
from viralai.graph.research_graph import ResearchGraph
from viralai.knowledge.models import LiteratureReference, MutationKnowledge
from viralai.knowledge.store import KnowledgeBase

# "ATGCAATAA": M-Q-stop, same fixture gene used across Phase 2/3 tests
REFERENCE_GENOME = "ATGCAATAA"
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]
VIRUS_NAME = "TestVirus"


def test_full_four_phase_pipeline(tmp_path_factory):
    # -- Phase 1: plugin data --
    graph = ResearchGraph()
    ingest_virus_and_genes(graph, VIRUS_NAME, GENE_ANNOTATIONS)

    # -- Phase 2: detect and classify a mutation --
    query_genome = "ATGCTATAA"  # single substitution at position 4 (Q -> L, missense)
    mutation_engine = MutationEngine()
    mutations = mutation_engine.detect_mutations(REFERENCE_GENOME, query_genome)
    assert len(mutations) == 1

    protein_engine = ProteinAnalysisEngine()
    protein_mutations = protein_engine.analyze(REFERENCE_GENOME, mutations, GENE_ANNOTATIONS)
    assert len(protein_mutations) == 1

    evolution_engine = EvolutionAnalysisEngine()
    entropy_by_position = evolution_engine.shannon_entropy_per_position(
        [REFERENCE_GENOME, query_genome]  # a tiny 2-genome "population" for this test
    )

    # -- Phase 3: Knowledge Base + Research Graph --
    ingest_mutations(graph, VIRUS_NAME, mutations, GENE_ANNOTATIONS)
    ingest_protein_mutations(graph, VIRUS_NAME, protein_mutations)

    kb = KnowledgeBase()
    kb.add_reference(
        LiteratureReference(reference_id="ref-1", citation="Fixture et al. 2024, J Virol")
    )
    kb.add_mutation_knowledge(
        MutationKnowledge(
            virus=VIRUS_NAME,
            gene="TESTGENE",
            position=4,
            reference_base="A",
            observed_base="T",
            known_effect_summary="Missense mutation affecting the test gene's product",
            evidence_level=EvidenceLevel.LEVEL_II_MULTI_STUDY,
            reference_ids=["ref-1"],
        )
    )
    ingest_knowledge_base(graph, VIRUS_NAME, kb)

    # sanity check the flagship compound query from Phase 3 still works here
    cited_mutations = graph.mutations_with_publications("TestVirus:gene:TESTGENE")
    assert cited_mutations == ["TestVirus:mutation:4:A>T"]

    # -- Phase 4: train a model on synthetic data, then reason about our real mutation --
    rng = np.random.RandomState(0)
    X_synthetic = rng.rand(100, len(FEATURE_NAMES))
    y_synthetic = (X_synthetic[:, 8] > 0.5).astype(int)  # index 8 = is_synonymous, arbitrary signal
    model = MutationHotspotModel()
    model.train(X_synthetic, y_synthetic)
    explainer = ShapExplainer(model)

    mutation = mutations[0]
    context = FeatureContext(
        genome_length=len(REFERENCE_GENOME),
        entropy_at_position=entropy_by_position[mutation.position],
        protein_mutation=protein_mutations[0],
    )

    # the feature vector itself should reflect the real Phase 2 classification
    features = extract_features(mutation, context)
    assert features["is_missense"] == 1.0
    to_vector([features])  # confirms it vectorizes without error

    reasoning_engine = ScientificReasoningEngine(graph)
    record = reasoning_engine.reason(VIRUS_NAME, mutation, context, model, explainer)

    # the reasoning record should reflect everything ingested in Phase 3
    assert record.affected_protein == "TestVirus:protein:TESTGENE"
    assert record.literature_citations == ["publication:ref-1"]
    assert record.evidence_level == EvidenceLevel.LEVEL_IV_COMPUTATIONAL
    assert 0.0 <= record.ai_confidence <= 1.0
    assert len(record.top_contributing_features) == 3
    assert (
        "research-use" in record.recommendation.lower()
        or "research use" in record.recommendation.lower()
    )

    # -- Phase 5: having identified a real mutation of interest, use the Simulation
    # Engine to explore a computational hypothesis: what happens to this position under
    # a selective pressure favoring the observed change? This is exactly the "simulate
    # before you sequence more" workflow the strategic plan describes.
    from viralai.simulation.encoding import encode as sim_encode
    from viralai.simulation.environmental_simulator import EnvironmentalPressure
    from viralai.simulation.laboratory import DigitalLaboratoryManager
    from viralai.simulation.population_simulator import SimulationConfig

    lab = DigitalLaboratoryManager(tmp_path_factory.mktemp("lab"))
    reference_encoded = sim_encode(REFERENCE_GENOME)
    pressure = EnvironmentalPressure(
        "hypothetical-selective-pressure", reference_encoded, {mutation.position: 2.0}
    )
    sim_config = SimulationConfig(population_size=30, generations=15, mutation_rate=0.05, seed=1)

    experiment = lab.run_experiment(
        name="e6-position-4-under-pressure",
        version="0.1.0",
        reference_genome=REFERENCE_GENOME,
        config=sim_config,
        fitness_function=pressure.fitness_function,
        notes=(
            "Exploring whether selective pressure favoring the observed missense change "
            "increases its prevalence in a simulated population -- computational "
            "hypothesis only, per Ch.13.6 not real biological evidence."
        ),
    )

    assert experiment.is_synthetic is True
    assert len(experiment.generation_summaries) <= 15  # may end early on extinction
    assert experiment.generation_summaries[-1]["mean_mutations_from_reference"] >= 0

    # -- Phase 6: assemble everything above into one exportable report --
    from viralai.reporting.report_builder import ReportBuilder
    from viralai.reporting.report_models import ReportProvenance
    from viralai.reporting import exporters as report_exporters
    from viralai.visualization.figures import plot_genome_map
    from viralai.visualization.plot_data import genome_map_from_mutations

    provenance = ReportProvenance(
        software_version="0.1.0",
        virus=VIRUS_NAME,
        plugin_name="fixture-plugin",
        plugin_version="0.1.0",
    )
    builder = ReportBuilder(provenance, "Full Pipeline Capstone Report")
    builder.add_mutations(
        mutations,
        protein_mutations=protein_mutations,
        reasoning_by_position={mutation.position: record},
    )
    builder.add_evolution_summary(evolution_engine, [REFERENCE_GENOME, query_genome])
    builder.add_simulation_experiment(experiment)
    builder.set_summary_notes("Generated by the five-phase capstone integration test.")

    report = builder.build()

    # every phase's contribution should be visible in the assembled report
    assert report.mutations[0].protein_classification == "missense"
    assert report.mutations[0].ai_flagged_as_hotspot is not None
    assert report.mutations[0].literature_citations == ["publication:ref-1"]
    assert report.evolution is not None
    assert len(report.simulations) == 1
    assert report.is_research_use_disclaimer_required is True

    # and every exporter should render it without error, disclaimer included
    markdown = report_exporters.to_markdown(report)
    assert report_exporters.RESEARCH_USE_DISCLAIMER in markdown
    assert "missense" in markdown
    report_exporters.to_json(report)
    report_exporters.to_csv(report)
    report_exporters.to_html(report)

    # and the genome map figure should render from the same mutation data
    plot_dir = tmp_path_factory.mktemp("plots")
    map_data = genome_map_from_mutations(mutations, genome_length=len(REFERENCE_GENOME))
    figure_path = plot_genome_map(map_data, plot_dir / "genome_map.png")
    assert figure_path.exists()
    assert figure_path.stat().st_size > 0

    # -- Phase 7: everything above happened outside any persistent project so far --
    # wrap it in a Research Workspace, the way a real researcher would actually work,
    # and re-run the mutation analysis through the checkpointed Workflow Runner so it's
    # recorded as a proper workflow execution rather than an ad hoc script run.
    from viralai.core.engine import CoreEngine
    from viralai.core.idm import AnalysisStatus
    from viralai.workflow.checkpoint import CheckpointManager
    from viralai.workflow.runner import WorkflowRunner
    from viralai.workflow.templates import mutation_analysis_workflow
    from viralai.workspace.models import ProjectMetadata, ProjectStatus
    from viralai.workspace.workspace import ResearchWorkspace

    project_root = tmp_path_factory.mktemp("project")
    workspace = ResearchWorkspace(
        project_root,
        ProjectMetadata(
            title="Capstone Six-Phase Project", principal_investigator="Test Researcher"
        ),
    )
    workspace.set_status(ProjectStatus.DATA_IMPORTED, note="fixture gene loaded")

    checkpoint_dir = tmp_path_factory.mktemp("checkpoints")
    runner = WorkflowRunner(CoreEngine(), CheckpointManager(checkpoint_dir))
    workflow_steps = mutation_analysis_workflow(REFERENCE_GENOME, query_genome, GENE_ANNOTATIONS)
    workflow_analysis = runner.run(
        "capstone-mutation-analysis", workflow_steps, run_id="capstone-mutation-analysis"
    )

    workspace.set_status(ProjectStatus.ANALYSIS_RUNNING)
    workspace.record_workflow_execution(workflow_analysis)
    workspace.store_analysis_result("mutation-summary", workflow_analysis.results)
    workspace.store_report("capstone-report", report, formats=("markdown", "json"))
    workspace.add_research_note(
        "Missense mutation at position 4 flagged by AI, backed by literature, "
        "explored further via simulation under selective pressure.",
        tags=["hypothesis", "TESTGENE"],
    )
    workspace.set_status(ProjectStatus.INTERPRETATION)

    # everything should be retrievable from the workspace afterward
    assert "capstone-mutation-analysis" in workspace.list_workflow_executions()
    assert "mutation-summary" in workspace.list_analyses()
    assert "capstone-report.md" in workspace.list_reports()
    assert "capstone-report.json" in workspace.list_reports()
    assert len(workspace.list_notes(tag="TESTGENE")) == 1
    assert workspace.metadata.status == ProjectStatus.INTERPRETATION
    assert (
        len(workspace.status_history()) == 4
    )  # created, data_imported, analysis_running, interpretation

    # and the workflow execution recorded in the workspace should match what actually ran
    reloaded_analysis = workspace.get_workflow_execution(workflow_analysis.analysis_id)
    assert reloaded_analysis.status == AnalysisStatus.COMPLETED
    assert len(reloaded_analysis.results["mutations"]) == 1
