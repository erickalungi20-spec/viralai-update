from viralai.ai.reasoning import ReasoningRecord
from viralai.core.idm import (
    EvidenceLevel,
    Mutation,
    MutationType,
    ProteinMutation,
    ProteinMutationClass,
)
from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.reporting.report_builder import ReportBuilder
from viralai.reporting.report_models import ReportProvenance
from viralai.simulation.laboratory import SimulationExperiment


def _provenance() -> ReportProvenance:
    return ReportProvenance(
        software_version="0.1.0", virus="TestVirus", plugin_name="hpv16", plugin_version="0.1.0"
    )


def _mutation(position: int = 4) -> Mutation:
    return Mutation(
        position=position,
        reference_base="A",
        observed_base="T",
        mutation_type=MutationType.SUBSTITUTION,
        confidence_score=0.9,
    )


def test_add_mutations_with_no_extra_context():
    builder = ReportBuilder(_provenance(), "Test Report")
    builder.add_mutations([_mutation()])

    report = builder.build()

    assert len(report.mutations) == 1
    entry = report.mutations[0]
    assert entry.position == 4
    assert entry.protein_classification is None
    assert entry.ai_flagged_as_hotspot is None


def test_add_mutations_preserves_supporting_evidence():
    mutation = _mutation()
    mutation.supporting_evidence.update(
        {
            "cds_name": "E6",
            "cds_position": 1,
            "gene_feature": "E6",
            "gene_feature_type": "orf",
            "genome_kind": "dna",
        }
    )
    builder = ReportBuilder(_provenance(), "Test Report")
    builder.add_mutations([mutation])

    entry = builder.build().mutations[0]
    assert entry.cds_name == "E6"
    assert entry.cds_position == 1
    assert entry.gene_feature == "E6"
    assert entry.gene_feature_type == "orf"
    assert entry.supporting_evidence["genome_kind"] == "dna"


def test_add_mutations_merges_protein_classification():
    mutation = _mutation()
    protein_mutation = ProteinMutation(
        source_mutation=mutation,
        protein_id="E6",
        position_aa=1,
        reference_aa="Q",
        observed_aa="L",
        classification=ProteinMutationClass.MISSENSE,
    )
    builder = ReportBuilder(_provenance(), "Test Report")
    builder.add_mutations([mutation], protein_mutations=[protein_mutation])

    entry = builder.build().mutations[0]

    assert entry.protein_classification == "missense"
    assert entry.affected_protein == "E6"
    assert entry.reference_aa == "Q"
    assert entry.observed_aa == "L"


def test_add_mutations_merges_ai_reasoning():
    mutation = _mutation()
    reasoning = ReasoningRecord(
        virus="TestVirus",
        mutation_summary="A4T",
        affected_protein="E6",
        literature_citations=["publication:ref-1"],
        evolutionary_conservation=0.5,
        ai_prediction_positive=True,
        ai_confidence=0.87,
        top_contributing_features=[("position_normalized", 0.3)],
        evidence_level=EvidenceLevel.LEVEL_IV_COMPUTATIONAL,
        recommendation="Test recommendation, research use only.",
    )
    builder = ReportBuilder(_provenance(), "Test Report")
    builder.add_mutations([mutation], reasoning_by_position={4: reasoning})

    entry = builder.build().mutations[0]

    assert entry.ai_flagged_as_hotspot is True
    assert entry.ai_confidence == 0.87
    assert entry.literature_citations == ["publication:ref-1"]


def test_add_evolution_summary():
    builder = ReportBuilder(_provenance(), "Test Report")
    engine = EvolutionAnalysisEngine()

    builder.add_evolution_summary(engine, ["ACGT", "ACTT", "ACGT"])

    evolution = builder.build().evolution
    assert evolution is not None
    assert evolution.population_size == 3
    assert evolution.nucleotide_diversity >= 0.0


def test_add_simulation_experiment():
    experiment = SimulationExperiment(
        experiment_id="exp-1",
        name="drift-test",
        version="0.1.0",
        config={"population_size": 10, "generations": 3, "mutation_rate": 0.01, "seed": 1},
        reference_genome_length=20,
        generation_summaries=[
            {
                "generation": 0,
                "nucleotide_diversity": 0.0,
                "mean_mutations_from_reference": 0.2,
                "population_extinct": False,
            },
            {
                "generation": 1,
                "nucleotide_diversity": 0.05,
                "mean_mutations_from_reference": 0.4,
                "population_extinct": False,
            },
        ],
        final_population_sample=["ACGT"],
        notes="test experiment",
    )
    builder = ReportBuilder(_provenance(), "Test Report")

    builder.add_simulation_experiment(experiment)

    sim_section = builder.build().simulations[0]
    assert sim_section.experiment_name == "drift-test"
    assert sim_section.generations_run == 2
    assert sim_section.final_mean_mutations_from_reference == 0.4
    assert sim_section.notes == "test experiment"


def test_set_summary_notes():
    builder = ReportBuilder(_provenance(), "Test Report")
    builder.set_summary_notes("This is a test summary.")

    assert builder.build().summary_notes == "This is a test summary."


def test_builder_methods_are_chainable():
    builder = ReportBuilder(_provenance(), "Test Report")
    result = builder.add_mutations([_mutation()]).set_summary_notes("chained")

    assert result is builder
    assert builder.build().summary_notes == "chained"
