"""
Graph ingestion.

Turns the outputs of Phase 1 (plugin gene annotations), Phase 2 (Mutation/ProteinMutation
engine output), and Phase 3's own Knowledge Base into ResearchGraph nodes and edges. This
module is what actually connects the three phases into one queryable graph — without it,
the Research Graph is just an empty data structure.
"""

from __future__ import annotations

from viralai.core.idm import Mutation, ProteinMutation
from viralai.graph.research_graph import ResearchGraph
from viralai.graph.types import NodeType, RelationType
from viralai.knowledge.store import KnowledgeBase


def ingest_virus_and_genes(
    graph: ResearchGraph, virus_name: str, gene_annotations: list[dict]
) -> None:
    """Add a Virus node and one Gene node per annotation, from a plugin's gene_annotations."""
    graph.add_node(virus_name, NodeType.VIRUS, name=virus_name)
    for gene in gene_annotations:
        gene_id = _gene_node_id(virus_name, gene["gene"])
        graph.add_node(
            gene_id,
            NodeType.GENE,
            gene_name=gene["gene"],
            start=gene["start"],
            end=gene["end"],
            virus=virus_name,
        )
        graph.add_edge(virus_name, RelationType.HAS_GENE, gene_id)


def ingest_mutations(
    graph: ResearchGraph,
    virus_name: str,
    mutations: list[Mutation],
    gene_annotations: list[dict],
) -> dict[int, str]:
    """Add a Mutation node per detected mutation and link it to whichever Gene node's
    coordinate range contains it (skipped if it falls outside every annotated gene, same
    convention as the Protein Analysis Engine). Returns a {mutation.position: node_id} map
    so callers (e.g. knowledge ingestion) can reference the nodes just created.
    """
    position_to_node_id: dict[int, str] = {}

    for mutation in mutations:
        mutation_id = _mutation_node_id(virus_name, mutation)
        graph.add_node(
            mutation_id,
            NodeType.MUTATION,
            position=mutation.position,
            reference_base=mutation.reference_base,
            observed_base=mutation.observed_base,
            mutation_type=mutation.mutation_type.value,
            confidence_score=mutation.confidence_score,
        )
        position_to_node_id[mutation.position] = mutation_id

        gene = _find_containing_gene(mutation.position, gene_annotations)
        if gene is not None:
            gene_id = _gene_node_id(virus_name, gene["gene"])
            graph.add_edge(mutation_id, RelationType.LOCATED_IN_GENE, gene_id)

    return position_to_node_id


def ingest_protein_mutations(
    graph: ResearchGraph, virus_name: str, protein_mutations: list[ProteinMutation]
) -> None:
    """Add Protein nodes (one per distinct protein_id seen) and AFFECTS_PROTEIN edges from
    each mutation to the protein it changes.
    """
    for pm in protein_mutations:
        protein_id = _protein_node_id(virus_name, pm.protein_id)
        graph.add_node(protein_id, NodeType.PROTEIN, protein_name=pm.protein_id, virus=virus_name)

        mutation_id = _mutation_node_id(virus_name, pm.source_mutation)
        if not graph.has_node(mutation_id):
            # defensive: protein mutations should always be ingested after their source
            # mutation, but don't silently drop the edge if ingestion order was different
            graph.add_node(
                mutation_id,
                NodeType.MUTATION,
                position=pm.source_mutation.position,
                reference_base=pm.source_mutation.reference_base,
                observed_base=pm.source_mutation.observed_base,
                mutation_type=pm.source_mutation.mutation_type.value,
                confidence_score=pm.source_mutation.confidence_score,
            )

        graph.add_edge(
            mutation_id,
            RelationType.AFFECTS_PROTEIN,
            protein_id,
            classification=pm.classification.value,
            reference_aa=pm.reference_aa,
            observed_aa=pm.observed_aa,
        )


def ingest_knowledge_base(
    graph: ResearchGraph, virus_name: str, knowledge_base: KnowledgeBase
) -> None:
    """Add Publication nodes for every LiteratureReference cited by this virus's
    MutationKnowledge entries, and DESCRIBED_BY edges from the matching Mutation node (if
    it exists in the graph) to each publication.
    """
    from viralai.knowledge.models import (
        KnowledgeQuery,
    )  # local import avoids a cycle at module load

    entries = knowledge_base.query_mutation_knowledge(KnowledgeQuery(virus=virus_name))
    for entry in entries:
        mutation_id = (
            f"{virus_name}:mutation:{entry.position}:{entry.reference_base}>{entry.observed_base}"
        )
        if not graph.has_node(mutation_id):
            continue  # this knowledge entry doesn't correspond to a mutation we've detected

        for reference_id in entry.reference_ids:
            reference = knowledge_base.get_reference(reference_id)
            publication_id = f"publication:{reference.reference_id}"
            graph.add_node(
                publication_id,
                NodeType.PUBLICATION,
                citation=reference.citation,
                doi=reference.doi,
                pubmed_id=reference.pubmed_id,
            )
            graph.add_edge(mutation_id, RelationType.DESCRIBED_BY, publication_id)


def _gene_node_id(virus_name: str, gene_name: str) -> str:
    return f"{virus_name}:gene:{gene_name}"


def _protein_node_id(virus_name: str, protein_id: str) -> str:
    return f"{virus_name}:protein:{protein_id}"


def _mutation_node_id(virus_name: str, mutation: Mutation) -> str:
    return f"{virus_name}:mutation:{mutation.position}:{mutation.reference_base}>{mutation.observed_base}"


def _find_containing_gene(position: int, gene_annotations: list[dict]) -> dict | None:
    for gene in gene_annotations:
        if gene["start"] - 1 <= position <= gene["end"] - 1:
            return gene
    return None
