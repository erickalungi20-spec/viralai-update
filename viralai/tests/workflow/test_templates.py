from viralai.core.engine import CoreEngine
from viralai.core.idm import AnalysisStatus, EvidenceLevel
from viralai.knowledge.models import LiteratureReference, MutationKnowledge
from viralai.knowledge.store import KnowledgeBase
from viralai.simulation.laboratory import DigitalLaboratoryManager
from viralai.simulation.population_simulator import SimulationConfig
from viralai.workflow.checkpoint import CheckpointManager
from viralai.workflow.runner import WorkflowRunner
from viralai.workflow.templates import (
    cancer_research_workflow,
    evolutionary_analysis_workflow,
    hiv_research_workflow,
    mutation_analysis_workflow,
    pandemic_surveillance_workflow,
    simulation_workflow,
)

# "ATGCAATAA": M-Q-stop, same fixture gene used across Phase 2/3/4 tests
REFERENCE_GENOME = "ATGCAATAA"
QUERY_GENOME = "ATGCTATAA"  # single missense substitution at position 4
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]
VIRUS_NAME = "TestVirus"


def _runner(tmp_path) -> WorkflowRunner:
    return WorkflowRunner(CoreEngine(), CheckpointManager(tmp_path))


def test_mutation_analysis_workflow(tmp_path):
    steps = mutation_analysis_workflow(REFERENCE_GENOME, QUERY_GENOME, GENE_ANNOTATIONS)
    analysis = _runner(tmp_path).run("mutation-analysis", steps)

    assert analysis.status == AnalysisStatus.COMPLETED
    assert len(analysis.results["mutations"]) == 1
    assert len(analysis.results["protein_mutations"]) == 1
    assert analysis.results["protein_mutations"][0]["classification"] == "missense"


def test_evolutionary_analysis_workflow(tmp_path):
    population = [REFERENCE_GENOME, QUERY_GENOME, REFERENCE_GENOME]
    steps = evolutionary_analysis_workflow(
        REFERENCE_GENOME, QUERY_GENOME, GENE_ANNOTATIONS, population
    )
    analysis = _runner(tmp_path).run("evolutionary-analysis", steps)

    assert analysis.status == AnalysisStatus.COMPLETED
    assert "evolution" in analysis.results
    assert analysis.results["evolution"]["population_size"] == 3


def test_cancer_research_workflow(tmp_path):
    kb = KnowledgeBase()
    kb.add_reference(LiteratureReference(reference_id="ref-1", citation="Fixture 2024"))
    kb.add_mutation_knowledge(
        MutationKnowledge(
            virus=VIRUS_NAME,
            gene="TESTGENE",
            position=4,
            reference_base="A",
            observed_base="T",
            known_effect_summary="Test oncogenic effect",
            evidence_level=EvidenceLevel.LEVEL_II_MULTI_STUDY,
            reference_ids=["ref-1"],
        )
    )

    steps = cancer_research_workflow(
        REFERENCE_GENOME, QUERY_GENOME, GENE_ANNOTATIONS, kb, VIRUS_NAME, "TESTGENE"
    )
    analysis = _runner(tmp_path).run("cancer-research", steps)

    assert analysis.status == AnalysisStatus.COMPLETED
    assert len(analysis.results["knowledge_entries"]) == 1
    assert (
        analysis.results["knowledge_entries"][0]["known_effect_summary"] == "Test oncogenic effect"
    )


def test_hiv_research_workflow(tmp_path):
    kb = KnowledgeBase()
    kb.add_reference(LiteratureReference(reference_id="ref-1", citation="Fixture 2024"))
    kb.add_mutation_knowledge(
        MutationKnowledge(
            virus=VIRUS_NAME,
            gene="TESTGENE",
            position=4,
            reference_base="A",
            observed_base="T",
            known_effect_summary="Test resistance mutation",
            evidence_level=EvidenceLevel.LEVEL_I_EXPERIMENTAL,
            reference_ids=["ref-1"],
        )
    )
    population = [REFERENCE_GENOME, QUERY_GENOME]

    steps = hiv_research_workflow(
        REFERENCE_GENOME, QUERY_GENOME, GENE_ANNOTATIONS, population, kb, VIRUS_NAME, "TESTGENE"
    )
    analysis = _runner(tmp_path).run("hiv-research", steps)

    assert analysis.status == AnalysisStatus.COMPLETED
    assert "evolution" in analysis.results
    assert len(analysis.results["knowledge_entries"]) == 1


def test_pandemic_surveillance_workflow(tmp_path):
    samples = [REFERENCE_GENOME, QUERY_GENOME, QUERY_GENOME]  # 2 of 3 carry the mutation

    steps = pandemic_surveillance_workflow(REFERENCE_GENOME, samples)
    analysis = _runner(tmp_path).run("pandemic-surveillance", steps)

    assert analysis.status == AnalysisStatus.COMPLETED
    surveillance = analysis.results["surveillance"]
    assert surveillance["sample_count"] == 3
    assert 4 in surveillance["hotspot_positions"]  # position 4 mutated in 2/3 samples


def test_simulation_workflow(tmp_path):
    lab = DigitalLaboratoryManager(tmp_path / "lab")
    config = SimulationConfig(population_size=10, generations=3, mutation_rate=0.05, seed=1)

    steps = simulation_workflow(
        lab, name="test-sim", version="0.1.0", reference_genome=REFERENCE_GENOME, config=config
    )
    analysis = _runner(tmp_path / "runner").run("simulation", steps)

    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.results["simulation_experiment"]["is_synthetic"] is True
    assert analysis.results["simulation_experiment"]["name"] == "test-sim"
