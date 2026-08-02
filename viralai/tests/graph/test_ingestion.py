from viralai.core.idm import EvidenceLevel, Mutation, MutationType
from viralai.engines.protein_engine import ProteinAnalysisEngine
from viralai.graph.ingestion import (
    ingest_knowledge_base,
    ingest_mutations,
    ingest_protein_mutations,
    ingest_virus_and_genes,
)
from viralai.graph.research_graph import ResearchGraph
from viralai.knowledge.models import KnowledgeQuery, LiteratureReference, MutationKnowledge
from viralai.knowledge.store import KnowledgeBase

# Same fixture gene used in Phase 2's protein engine tests: "ATGCAATAA" = M-Q-stop
REFERENCE_GENOME = "ATGCAATAA"
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


def test_ingest_virus_and_genes_creates_expected_nodes():
    graph = ResearchGraph()
    ingest_virus_and_genes(graph, "TestVirus", GENE_ANNOTATIONS)

    assert graph.has_node("TestVirus")
    assert graph.has_node("TestVirus:gene:TESTGENE")
    assert graph.neighbors("TestVirus") == ["TestVirus:gene:TESTGENE"]


def test_ingest_mutations_links_to_containing_gene():
    graph = ResearchGraph()
    ingest_virus_and_genes(graph, "TestVirus", GENE_ANNOTATIONS)

    mutation = Mutation(
        position=4, reference_base="A", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    position_map = ingest_mutations(graph, "TestVirus", [mutation], GENE_ANNOTATIONS)

    mutation_id = position_map[4]
    assert graph.has_node(mutation_id)
    assert graph.mutations_for_gene("TestVirus:gene:TESTGENE") == [mutation_id]


def test_ingest_mutations_outside_any_gene_creates_node_without_gene_link():
    graph = ResearchGraph()
    ingest_virus_and_genes(graph, "TestVirus", GENE_ANNOTATIONS)

    mutation = Mutation(
        position=500, reference_base="A", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    position_map = ingest_mutations(graph, "TestVirus", [mutation], GENE_ANNOTATIONS)

    mutation_id = position_map[500]
    assert graph.has_node(mutation_id)
    assert graph.neighbors(mutation_id) == []  # no LOCATED_IN_GENE edge


def test_ingest_protein_mutations_creates_protein_node_and_edge():
    graph = ResearchGraph()
    ingest_virus_and_genes(graph, "TestVirus", GENE_ANNOTATIONS)

    mutation = Mutation(
        position=4, reference_base="A", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    ingest_mutations(graph, "TestVirus", [mutation], GENE_ANNOTATIONS)

    protein_engine = ProteinAnalysisEngine()
    protein_mutations = protein_engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    ingest_protein_mutations(graph, "TestVirus", protein_mutations)

    assert graph.has_node("TestVirus:protein:TESTGENE")
    mutation_id = "TestVirus:mutation:4:A>T"
    assert "TestVirus:protein:TESTGENE" in graph.neighbors(mutation_id, direction="out")


def test_full_pipeline_answers_the_flagship_compound_query():
    """Reproduces the exact query the strategic plan uses as ViralAI's differentiator:
    'mutations in a gene that are backed by a publication.' Exercises plugin gene
    annotations (Phase 1) -> Mutation/Protein engines (Phase 2) -> Knowledge Base +
    Research Graph (Phase 3) end to end.
    """
    graph = ResearchGraph()
    kb = KnowledgeBase()

    # Phase 1: plugin data
    ingest_virus_and_genes(graph, "TestVirus", GENE_ANNOTATIONS)

    # Phase 2: two mutations detected in the same gene
    documented_mutation = Mutation(
        position=3, reference_base="C", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    undocumented_mutation = Mutation(
        position=5, reference_base="A", observed_base="G", mutation_type=MutationType.SUBSTITUTION
    )
    ingest_mutations(
        graph, "TestVirus", [documented_mutation, undocumented_mutation], GENE_ANNOTATIONS
    )

    protein_engine = ProteinAnalysisEngine()
    protein_mutations = protein_engine.analyze(
        REFERENCE_GENOME, [documented_mutation, undocumented_mutation], GENE_ANNOTATIONS
    )
    ingest_protein_mutations(graph, "TestVirus", protein_mutations)

    # Phase 3: only the first mutation has a published knowledge entry
    kb.add_reference(LiteratureReference(reference_id="ref-1", citation="Fixture et al. 2024"))
    kb.add_mutation_knowledge(
        MutationKnowledge(
            virus="TestVirus",
            gene="TESTGENE",
            position=3,
            reference_base="C",
            observed_base="T",
            known_effect_summary="Nonsense mutation, truncates protein",
            evidence_level=EvidenceLevel.LEVEL_I_EXPERIMENTAL,
            reference_ids=["ref-1"],
        )
    )
    ingest_knowledge_base(graph, "TestVirus", kb)

    # The compound query: which mutations in TESTGENE are backed by a publication?
    result = graph.mutations_with_publications("TestVirus:gene:TESTGENE")

    assert result == ["TestVirus:mutation:3:C>T"]
    assert "TestVirus:mutation:5:A>G" not in result

    # sanity check the KB's own query still works standalone
    kb_results = kb.query_mutation_knowledge(KnowledgeQuery(virus="TestVirus", gene="TESTGENE"))
    assert len(kb_results) == 1
