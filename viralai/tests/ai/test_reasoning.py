import numpy as np

from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FEATURE_NAMES, FeatureContext
from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.reasoning import ScientificReasoningEngine
from viralai.core.idm import EvidenceLevel, Mutation, MutationType
from viralai.graph.research_graph import ResearchGraph
from viralai.graph.types import NodeType, RelationType


def _trained_model_and_explainer() -> tuple[MutationHotspotModel, ShapExplainer]:
    rng = np.random.RandomState(0)
    X = rng.rand(80, len(FEATURE_NAMES))
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    model.train(X, y)
    return model, ShapExplainer(model)


def _mutation() -> Mutation:
    return Mutation(
        position=4,
        reference_base="A",
        observed_base="T",
        mutation_type=MutationType.SUBSTITUTION,
        confidence_score=0.9,
    )


def test_reasoning_without_any_graph_data_still_produces_a_record():
    graph = ResearchGraph()  # empty -- mutation isn't even in the graph
    model, explainer = _trained_model_and_explainer()
    engine = ScientificReasoningEngine(graph)

    record = engine.reason(
        "TestVirus", _mutation(), FeatureContext(genome_length=1000), model, explainer
    )

    assert record.affected_protein is None
    assert record.literature_citations == []
    assert record.evidence_level == EvidenceLevel.LEVEL_IV_COMPUTATIONAL
    assert (
        "research-use" in record.recommendation.lower()
        or "research use" in record.recommendation.lower()
    )


def test_reasoning_finds_affected_protein_and_citations_from_graph():
    graph = ResearchGraph()
    mutation = _mutation()
    mutation_id = "TestVirus:mutation:4:A>T"

    graph.add_node(mutation_id, NodeType.MUTATION, position=4)
    graph.add_node("TestVirus:protein:E6", NodeType.PROTEIN, protein_name="E6")
    graph.add_node("publication:ref-1", NodeType.PUBLICATION, citation="Fixture et al. 2024")

    graph.add_edge(mutation_id, RelationType.AFFECTS_PROTEIN, "TestVirus:protein:E6")
    graph.add_edge(mutation_id, RelationType.CITED_BY, "publication:ref-1")

    model, explainer = _trained_model_and_explainer()
    engine = ScientificReasoningEngine(graph)

    record = engine.reason(
        "TestVirus", mutation, FeatureContext(genome_length=1000), model, explainer
    )

    assert record.affected_protein == "TestVirus:protein:E6"
    assert record.literature_citations == ["publication:ref-1"]
    assert "review the cited sources" in record.recommendation


def test_recommendation_never_contains_clinical_language():
    graph = ResearchGraph()
    model, explainer = _trained_model_and_explainer()
    engine = ScientificReasoningEngine(graph)

    record = engine.reason(
        "TestVirus", _mutation(), FeatureContext(genome_length=1000), model, explainer
    )

    forbidden_terms = ["diagnosis", "diagnose", "treatment", "prescribe", "clinical recommendation"]
    lowered = record.recommendation.lower()
    for term in forbidden_terms:
        assert term not in lowered


def test_top_contributing_features_has_three_entries():
    graph = ResearchGraph()
    model, explainer = _trained_model_and_explainer()
    engine = ScientificReasoningEngine(graph)

    record = engine.reason(
        "TestVirus", _mutation(), FeatureContext(genome_length=1000), model, explainer
    )

    assert len(record.top_contributing_features) == 3
