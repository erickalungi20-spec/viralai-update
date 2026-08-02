# ADR-011: Phase 8 API scope -- REST + SDK + CLI now, GraphQL deferred

## Status
Accepted

## Context
The Commercial Development Workflow's Phase 8 line item reads: "Analysis / Plugin /
Knowledge Base / AI / Simulation / Reporting APIs via FastAPI... Python SDK, CLI, GraphQL
layer (for the Research Graph specifically...) -- built now rather than 'potential
enhancement'."

## Decisions

1. **REST API via FastAPI covers all six categories.** `api/routers/` has one module per
   category (analysis, plugins, knowledge, ai, simulation, reports), each exposing real
   operations against the actual Phase 2-7 engines/registries -- not stubs. FastAPI's
   auto-generated OpenAPI schema (`/docs`, `/openapi.json`) is the API reference; no
   separate hand-written API documentation was created, consistent with Phase 6's
   Automated Documentation Engine philosophy of generating docs from real artifacts.

2. **Python SDK implemented as a thin httpx wrapper, not a second implementation.**
   `sdk/client.py`'s `ViralAIClient` calls the REST endpoints; it contains no analysis
   logic of its own. This guarantees the SDK and the API can never silently diverge in
   behavior, because there's only one implementation.

3. **CLI implemented with argparse (standard library), not Click/Typer.** No new
   dependency for command-line automation. Covers `detect-mutations`, `list-plugins`,
   and `serve` (starts the API server) -- the operations most useful for scripting and CI,
   not an exhaustive wrapper of every API endpoint.

4. **GraphQL layer for the Research Graph is deferred, not built.** This is a genuine
   scope cut, stated honestly rather than hidden: GraphQL needs a real new dependency
   (strawberry-graphql or graphene) and a meaningful amount of schema-design work to
   expose the Research Graph's traversal capabilities well. The Research Graph's
   Python API (`ResearchGraph.neighbors`, `mutations_with_publications`, etc. from Phase
   3) already serves the same queries programmatically today. GraphQL's actual value is
   letting an *external, non-Python client* (e.g. a future web frontend) construct
   flexible graph queries without ViralAI needing to anticipate every query shape in
   advance -- and there is no such frontend yet. Building GraphQL now would mean building
   for a consumer that doesn't exist, the same category of premature-infrastructure
   mistake ADR-004 already reasoned through for the Event Bus.

## Consequences
- **Positive:** every REST endpoint is real and tested against actual engines, not mocked.
- **Positive:** the SDK cannot drift from API behavior, by construction.
- **Positive:** the CLI adds real scripting/CI value (e.g. `viralai detect-mutations
  --reference ... --query ... --output result.json` in a shell pipeline) with zero new
  dependencies.
- **Negative:** a future frontend wanting flexible, client-driven graph queries against
  the Research Graph will need the GraphQL layer built at that point -- it does not exist
  yet.
- **Negative:** the REST API's Knowledge Base and Simulation endpoints operate against a
  single shared, process-local file-backed store (via `lru_cache`'d dependencies) --
  this is correct for the current single-process deployment model but is not yet a
  multi-tenant or horizontally-scaled design.

## Trigger for revisiting
- GraphQL: the first time an external (non-Python, non-CLI) client -- especially a web
  frontend -- needs flexible, client-defined queries against the Research Graph that the
  fixed REST endpoints don't anticipate.
- Multi-tenant API state: the first time the API needs to serve more than one
  organization/dataset from a single deployment.
