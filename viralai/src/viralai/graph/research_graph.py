"""
Research Graph (Blueprint's flagship cross-entity query capability, from the engineering
review's "Recommendation 8").

Phase 3 implementation: an in-memory `networkx.MultiDiGraph`, not a Neo4j-backed graph
database. Same pragmatic reasoning as Phase 0's Event Bus/Task Scheduler and Phase 3's
Knowledge Base store — networkx is a mature, well-tested, dependency-light graph library
with no server to run, so it's the correct choice for "working and correct now," with a
documented path to a Neo4j-backed implementation when query volume or graph size actually
requires it (see ADR-006).
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger
from viralai.graph.types import NodeType, RelationType

logger = get_logger("graph.research_graph")


class ResearchGraph:
    """A typed, directed multigraph of research entities and their relationships."""

    def __init__(self) -> None:
        self._graph = nx.MultiDiGraph()

    # -- mutation ------------------------------------------------------------------------

    def add_node(self, node_id: str, node_type: NodeType, **attributes: Any) -> None:
        """Add or update a node. Re-adding an existing id merges attributes rather than
        raising — this matters because the same Virus/Gene node gets referenced by many
        ingestion calls (one per mutation, one per publication, etc).
        """
        if self._graph.has_node(node_id):
            existing_type = self._graph.nodes[node_id]["node_type"]
            if existing_type != node_type:
                raise ValidationError(
                    f"Node '{node_id}' already exists with type '{existing_type}', "
                    f"cannot re-add as '{node_type}'"
                )
            self._graph.nodes[node_id].update(attributes)
            return
        self._graph.add_node(node_id, node_type=node_type, **attributes)

    def add_edge(
        self, source_id: str, relation: RelationType, target_id: str, **attributes: Any
    ) -> None:
        for node_id in (source_id, target_id):
            if not self._graph.has_node(node_id):
                raise ValidationError(f"Cannot add edge: node '{node_id}' does not exist yet")
        self._graph.add_edge(
            source_id, target_id, key=relation.value, relation=relation, **attributes
        )

    # -- query ---------------------------------------------------------------------------

    def get_node(self, node_id: str) -> dict[str, Any]:
        if not self._graph.has_node(node_id):
            raise ValidationError(f"No node with id '{node_id}'")
        return dict(self._graph.nodes[node_id])

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def nodes_by_type(self, node_type: NodeType) -> list[str]:
        return [n for n, data in self._graph.nodes(data=True) if data.get("node_type") == node_type]

    def neighbors(
        self, node_id: str, *, relation: RelationType | None = None, direction: str = "out"
    ) -> list[str]:
        """Node ids connected to `node_id`, optionally filtered by relation type.
        `direction`: "out" (default, outgoing edges), "in" (incoming edges), or "both".
        """
        if not self._graph.has_node(node_id):
            raise ValidationError(f"No node with id '{node_id}'")

        results: set[str] = set()
        if direction in ("out", "both"):
            for _, target, data in self._graph.out_edges(node_id, data=True):
                if relation is None or data.get("relation") == relation:
                    results.add(target)
        if direction in ("in", "both"):
            for source, _, data in self._graph.in_edges(node_id, data=True):
                if relation is None or data.get("relation") == relation:
                    results.add(source)
        return sorted(results)

    def mutations_for_gene(self, gene_id: str) -> list[str]:
        """All Mutation node ids with a LOCATED_IN_GENE edge to `gene_id`."""
        return self.neighbors(gene_id, relation=RelationType.LOCATED_IN_GENE, direction="in")

    def publications_for_mutation(self, mutation_id: str) -> list[str]:
        """All Publication node ids linked to `mutation_id` via CITED_BY/DESCRIBED_BY."""
        cited = self.neighbors(mutation_id, relation=RelationType.CITED_BY, direction="out")
        described = self.neighbors(mutation_id, relation=RelationType.DESCRIBED_BY, direction="out")
        return sorted(set(cited) | set(described))

    def mutations_with_publications(self, gene_id: str) -> list[str]:
        """The compound query that motivates having a graph at all: mutations in a gene
        that are backed by at least one citable publication — i.e. not purely
        computational predictions. This is the kind of question that requires joining
        across Gene -> Mutation -> Publication in one traversal rather than three
        separate lookups against three separate tables.
        """
        return [m for m in self.mutations_for_gene(gene_id) if self.publications_for_mutation(m)]

    # -- introspection ---------------------------------------------------------------------

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, data in self._graph.nodes(data=True):
            node_type = data.get("node_type")
            key = node_type.value if isinstance(node_type, NodeType) else str(node_type)
            counts[key] = counts.get(key, 0) + 1
        counts["_edges"] = self._graph.number_of_edges()
        return counts

    def __len__(self) -> int:
        return self._graph.number_of_nodes()
