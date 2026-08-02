# ADR-006: Phase 3 Research Graph uses in-memory networkx, not Neo4j

## Status
Accepted

## Context
The Commercial Development Workflow specifies Neo4j for the Research Graph, positioned as
the flagship differentiator (cross-entity queries like "mutations in gene X backed by a
publication"). Standing up and maintaining a Neo4j instance is real operational overhead
— before there is enough data volume or query concurrency to need a dedicated graph
database server.

## Decision
Phase 3 implements the Research Graph as an in-memory `networkx.MultiDiGraph`
(`viralai.graph.research_graph.ResearchGraph`), with a typed node/edge vocabulary
(`viralai.graph.types`) and ingestion functions that populate it from plugin data, engine
output, and the Knowledge Base.

Unlike the Event Bus and Task Scheduler (ADR-004), this is not a "reimplemented in pure
Python to avoid a dependency" decision — `networkx` is a mature, well-tested, pip-installable
library with no server component, so using it *is* the pragmatic choice, not a placeholder
for one. What's deferred is specifically the *Neo4j-backed, server-based* version.

## Consequences
- **Positive:** the compound cross-entity queries the Research Graph exists to enable
  (`mutations_with_publications`, `neighbors` traversal) work correctly today, fully
  tested, with zero infrastructure to run or maintain.
- **Positive:** networkx's graph algorithms (shortest path, subgraph extraction,
  centrality measures) are available for free if later query needs grow beyond the
  hand-written query methods in `ResearchGraph`.
- **Negative:** the graph is rebuilt in memory on every process start — no persistence
  layer yet. Fine for a single research session or test run; not fine for a
  multi-user/long-lived deployment, which needs the graph state to survive a restart.
- **Negative:** does not scale past single-machine memory. BV-BRC-scale data volumes
  (15 million viral genomes) would not fit in an in-memory graph.

## Trigger for revisiting
The first time either of these becomes true:
1. The graph needs to persist across process restarts for a real multi-user deployment
   (Phase 11-era concern), or
2. Node/edge counts approach single-machine memory limits.

At that point, swap in a Neo4j-backed implementation of the same `ResearchGraph` interface
(`add_node`, `add_edge`, `neighbors`, the compound query methods) — the ingestion functions
in `viralai.graph.ingestion` should not need to change, only what they're ingesting into.

## Alternatives considered
- **Neo4j from day one.** Rejected for the same reason as ADR-004's Redis/Celery
  deferral — real operational cost with no current load that justifies it.
- **Hand-rolled graph structure (adjacency lists, no library).** Rejected — unlike the
  Event Bus/Scheduler, a graph traversal library is a solved problem with meaningful
  correctness risk if reimplemented casually. Depending on networkx here is better
  engineering, not a shortcut.
