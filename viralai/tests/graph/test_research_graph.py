import pytest

from viralai.common.errors import ValidationError
from viralai.graph.research_graph import ResearchGraph
from viralai.graph.types import NodeType, RelationType


def test_add_node_and_get_node():
    graph = ResearchGraph()
    graph.add_node("HPV16", NodeType.VIRUS, name="HPV16")
    node = graph.get_node("HPV16")
    assert node["node_type"] == NodeType.VIRUS
    assert node["name"] == "HPV16"


def test_get_missing_node_raises():
    graph = ResearchGraph()
    with pytest.raises(ValidationError):
        graph.get_node("nonexistent")


def test_re_adding_same_node_merges_attributes():
    graph = ResearchGraph()
    graph.add_node("HPV16", NodeType.VIRUS, name="HPV16")
    graph.add_node("HPV16", NodeType.VIRUS, extra_field="added later")

    node = graph.get_node("HPV16")
    assert node["name"] == "HPV16"
    assert node["extra_field"] == "added later"
    assert len(graph) == 1  # still one node, not two


def test_re_adding_with_different_type_raises():
    graph = ResearchGraph()
    graph.add_node("X", NodeType.VIRUS)
    with pytest.raises(ValidationError):
        graph.add_node("X", NodeType.GENE)


def test_add_edge_requires_both_nodes_to_exist():
    graph = ResearchGraph()
    graph.add_node("HPV16", NodeType.VIRUS)
    with pytest.raises(ValidationError):
        graph.add_edge("HPV16", RelationType.HAS_GENE, "E6")


def test_add_edge_and_neighbors():
    graph = ResearchGraph()
    graph.add_node("HPV16", NodeType.VIRUS)
    graph.add_node("HPV16:gene:E6", NodeType.GENE)
    graph.add_edge("HPV16", RelationType.HAS_GENE, "HPV16:gene:E6")

    neighbors = graph.neighbors("HPV16", relation=RelationType.HAS_GENE)
    assert neighbors == ["HPV16:gene:E6"]


def test_neighbors_direction_in_vs_out():
    graph = ResearchGraph()
    graph.add_node("A", NodeType.VIRUS)
    graph.add_node("B", NodeType.GENE)
    graph.add_edge("A", RelationType.HAS_GENE, "B")

    assert graph.neighbors("A", direction="out") == ["B"]
    assert graph.neighbors("B", direction="in") == ["A"]
    assert graph.neighbors("A", direction="in") == []


def test_nodes_by_type():
    graph = ResearchGraph()
    graph.add_node("HPV16", NodeType.VIRUS)
    graph.add_node("HPV16:gene:E6", NodeType.GENE)
    graph.add_node("HPV16:gene:E7", NodeType.GENE)

    genes = graph.nodes_by_type(NodeType.GENE)
    assert sorted(genes) == ["HPV16:gene:E6", "HPV16:gene:E7"]
    assert graph.nodes_by_type(NodeType.VIRUS) == ["HPV16"]


def test_mutations_for_gene_and_publications_for_mutation():
    graph = ResearchGraph()
    graph.add_node("gene:E6", NodeType.GENE)
    graph.add_node("mutation:1", NodeType.MUTATION)
    graph.add_node("pub:1", NodeType.PUBLICATION)

    graph.add_edge("mutation:1", RelationType.LOCATED_IN_GENE, "gene:E6")
    graph.add_edge("mutation:1", RelationType.CITED_BY, "pub:1")

    assert graph.mutations_for_gene("gene:E6") == ["mutation:1"]
    assert graph.publications_for_mutation("mutation:1") == ["pub:1"]


def test_mutations_with_publications_filters_to_cited_mutations_only():
    graph = ResearchGraph()
    graph.add_node("gene:E6", NodeType.GENE)
    graph.add_node("mutation:cited", NodeType.MUTATION)
    graph.add_node("mutation:uncited", NodeType.MUTATION)
    graph.add_node("pub:1", NodeType.PUBLICATION)

    graph.add_edge("mutation:cited", RelationType.LOCATED_IN_GENE, "gene:E6")
    graph.add_edge("mutation:uncited", RelationType.LOCATED_IN_GENE, "gene:E6")
    graph.add_edge("mutation:cited", RelationType.CITED_BY, "pub:1")

    result = graph.mutations_with_publications("gene:E6")

    assert result == ["mutation:cited"]


def test_summary_counts_nodes_by_type_and_edges():
    graph = ResearchGraph()
    graph.add_node("HPV16", NodeType.VIRUS)
    graph.add_node("gene:E6", NodeType.GENE)
    graph.add_node("gene:E7", NodeType.GENE)
    graph.add_edge("HPV16", RelationType.HAS_GENE, "gene:E6")
    graph.add_edge("HPV16", RelationType.HAS_GENE, "gene:E7")

    summary = graph.summary()

    assert summary["virus"] == 1
    assert summary["gene"] == 2
    assert summary["_edges"] == 2
