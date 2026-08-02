# ViralAI

An AI-powered, modular, virus-agnostic viral genomics research and simulation platform.

This repository is the **Phase 0 Foundation Layer** build, following the ViralAI Commercial
Development Workflow. Phase 0 exists to give every later engine (Mutation, Protein, Evolution,
AI, Simulation) a common, tested substrate to build on: a shared data model, metadata handling,
caching, event-driven communication, background job scheduling, and workflow orchestration.

## Status

`v0.1.0` — Phases 0 through 10 are built and tested: Foundation, Plugin System, Core
Scientific Engines, Knowledge Base + Research Graph, AI Engine + Training Pipeline
Manager, Simulation Engine + Digital Laboratory Manager, Reporting/Visualization/
Documentation Engine, Workflow Engine + Research Workspace, API Layer, Security &
Responsible AI, and Testing/Benchmarking/CI/CD + Development Dashboard. See `docs/adr/`
for design decisions and `docs/PLUGIN_DEVELOPMENT_STANDARD.md` for the plugin contract.

**Phase 10:**
- **Test pyramid made queryable** — `pytest -m unit|integration|system|plugin|performance`
  all work, via automatic path-based classification in the root `conftest.py`, not by
  hand-annotating ~450 tests.
- **Benchmark Repository** — synthetic datasets with ground truth known exactly by
  construction (real per-virus benchmarks await real reference genomes — see ADR-013,
  same policy as the HPV16 plugin's reference data). `viralai dashboard --run-benchmarks`
  runs them and reports pass/fail.
- **Reproducibility harness** — `assert_reproducible()` generalizes Phase 5's simulation
  replay check into a reusable utility, now also gating CI directly.
- **Sci-CI pipeline** — every gate (system tests, plugin security scan, benchmark suite,
  reproducibility check) was manually run and verified to fail correctly before being
  wired into `.github/workflows/ci.yml` — not written and hoped to work.
- **Development Dashboard** — `viralai dashboard` aggregates module completion, plugin
  certification + live security scan status, registered AI model metrics, benchmark
  pass/fail, and a live documentation-gap count into one Markdown report with an explicit
  `release_ready` flag, uploaded as a CI artifact on every run.

**First plugin:** `plugins/hpv16/` — HPV16, certification tier `experimental`, passes its
own security scan (`test_real_hpv16_plugin_is_clean`). Ships verified E6/E7 gene
coordinates with literature citations. Does **not** ship the real reference genome
sequence (see `plugins/hpv16/data/reference/README.md`) — reference sequences are
provisioned locally from a verifiable source, never committed or fabricated.

## Why this looks smaller than the full Blueprint

Phase 0 deliberately ships **lightweight, in-process implementations** of the Event Bus and Task
Scheduler (pure Python, no Redis/Celery required) so the foundation can be built, tested, and
run on a single developer machine with zero external infrastructure. Both are built behind the
same interface the production versions (Redis Streams, Celery) will implement later — see
`docs/adr/ADR-004-phase0-pragmatic-infrastructure.md` for the reasoning. This is a deliberate
scope decision, not a shortcut: the goal is a working, testable foundation now, with a clean
swap-in path to distributed infrastructure once there's an actual reason to pay for it (multi-user
load, real background job volume, cloud deployment).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
```

Run the API server:

```bash
viralai issue-api-key --label you --role admin   # bootstrap: prints a raw key, shown once
viralai serve --port 8000
# then open http://127.0.0.1:8000/docs for interactive OpenAPI docs
# pass the issued key as the X-API-Key header for write operations (knowledge writes,
# AI predictions, simulation runs) -- reads work without auth
```

Or use the CLI directly, no server needed:

```bash
viralai detect-mutations --reference ACGT... --query ACGA... --output result.json
viralai list-plugins --plugins-dir plugins
viralai dashboard --plugins-dir plugins --data-dir .viralai_api_data --run-benchmarks
```

## Repository layout

```
src/viralai/
    common/         # Common Services Layer: logging, config, errors, file I/O, validation, IDs
    core/
        idm.py           # Internal Data Model (Genome, Mutation, Protein, Variant, Analysis)
        metadata.py      # Unified Metadata Engine — every IDM object auto-inherits provenance fields
        cache.py         # Scientific Cache — memoization for expensive/repeated computations
        event_bus.py     # Event Bus — decoupled engine-to-engine communication
        scheduler.py     # Task Scheduler — background/long-running job management
        provenance.py    # Provenance Manager — records what/how/when for reproducibility
        plugin_manager.py # Plugin discovery, validation, registration (Phase 1 hook point)
        engine.py        # Core Engine — orchestrates the above into a workflow lifecycle
tests/                # One test module per core component
docs/adr/             # Architecture Decision Records

src/viralai/plugins/    # Phase 1: manifest spec, VirusPlugin base, reference loader, discovery
    manifest.py            # PluginManifest + CertificationTier (experimental/community/official)
    base.py                 # VirusPlugin ABC every virus plugin subclasses
    reference.py             # Reference genome load/validate — refuses to run on bad data
    loader.py                 # discover_plugins() — scans a directory, validates, imports

plugins/<name>/         # Content plugins live outside src/ — they're data, not engine code
    manifest.json
    __init__.py            # defines a `Plugin` class
    data/
    tests/
src/viralai/engines/    # Phase 2: the first engines that produce real scientific output
    genetic_code.py         # standard codon table + translate()
    alignment.py              # Needleman-Wunsch global alignment (used only when lengths differ)
    mutation_engine.py         # MutationEngine — reference vs query -> list[Mutation]
    protein_engine.py           # ProteinAnalysisEngine — Mutation -> ProteinMutation classification
    evolution_engine.py          # EvolutionAnalysisEngine — entropy, diversity, hotspots

src/viralai/knowledge/   # Phase 3: curated, cited, evidence-level-tagged knowledge
    models.py                # LiteratureReference, MutationKnowledge, ProteinKnowledge
    store.py                   # KnowledgeBase — file-backed, in-memory indexed

src/viralai/graph/        # Phase 3: the Research Graph (flagship differentiator)
    types.py                  # NodeType / RelationType vocabulary
    research_graph.py           # ResearchGraph — in-memory networkx.MultiDiGraph wrapper
    ingestion.py                  # connects plugin data + engine output + Knowledge Base

src/viralai/ai/            # Phase 4: AI Engine + Training Pipeline Manager
    features.py                # Mutation -> fixed-order numeric feature vector
    hotspot_model.py             # MutationHotspotModel — Random Forest baseline
    explainability.py              # ShapExplainer — real per-prediction SHAP attribution
    registry.py                      # ModelRegistry — versioned, file-backed model storage
    training_pipeline.py               # AITrainingPipelineManager — the enforced training process
    reasoning.py                         # ScientificReasoningEngine — queries the Research Graph

src/viralai/simulation/    # Phase 5: Simulation Engine + Digital Laboratory Manager
    encoding.py                 # nucleotide <-> integer encoding for numpy vectorization
    mutation_simulator.py         # Jukes-Cantor substitution model
    selection_simulator.py          # Wright-Fisher fitness-weighted reproduction
    environmental_simulator.py        # per-position selective pressure (drug/immune)
    population_simulator.py             # orchestrates mutation + selection across generations
    laboratory.py                         # DigitalLaboratoryManager — experiments: run/replay/compare

src/viralai/reporting/     # Phase 6: Reporting Engine
    report_models.py           # AnalysisReport and its sections (pydantic)
    report_builder.py            # ReportBuilder — assembles a report from Phase 2-5 output
    exporters.py                   # Markdown, JSON, CSV, HTML exporters

src/viralai/visualization/  # Phase 6: Visualization Engine
    plot_data.py                # plot-ready data models (no matplotlib dependency)
    figures.py                    # matplotlib static PNG rendering

src/viralai/docs_engine/    # Phase 6: Automated Documentation Engine
    api_reference.py             # introspection-based Markdown API reference
    dependency_graph.py            # AST-based import graph, DOT export, cycle detection

src/viralai/workflow/      # Phase 7: Workflow Engine
    checkpoint.py               # CheckpointManager — persists progress after every step
    runner.py                     # WorkflowRunner — checkpointing + retry on top of CoreEngine
    templates.py                    # the six named workflow templates (Ch.17.4)

src/viralai/workspace/     # Phase 7: Research Workspace
    models.py                    # ProjectMetadata, ProjectStatus, ResearchNote
    workspace.py                   # ResearchWorkspace — one project = one persistent directory

src/viralai/api/           # Phase 8: REST API (FastAPI)
    app.py                     # FastAPI app, mounts every router
    dependencies.py              # shared registry instances (env-var configurable storage)
    schemas.py                     # API-specific request/response models
    routers/                         # analysis.py, plugins.py, knowledge.py, ai.py,
                                      # simulation.py, reports.py -- one per Ch.30 category

src/viralai/sdk/           # Phase 8: Python SDK
    client.py                    # ViralAIClient -- thin httpx wrapper, no logic of its own

src/viralai/cli.py         # Phase 8: CLI (argparse, stdlib only) -- `viralai` command

src/viralai/security/      # Phase 9: framework-agnostic security primitives
    roles.py                   # Role (VIEWER/RESEARCHER/ADMIN) ordering
    api_keys.py                   # APIKeyStore -- hashed key issuance/verification
    encryption.py                    # Fernet encryption at rest
    audit.py                            # append-only AuditLogger
    plugin_scanner.py                     # static AST-based plugin security scan
    responsible_ai.py                       # ResponsibleAIEnvelope

src/viralai/api/auth.py    # Phase 9: FastAPI auth wiring (X-API-Key, require_role)

src/viralai/benchmarking/  # Phase 10: Benchmark Repository + Reproducibility
    datasets.py                 # synthetic datasets with known-by-construction ground truth
    runner.py                     # scores engines against datasets
    repository.py                   # file-backed run history
    reproducibility.py                # assert_reproducible() — general-purpose determinism check

src/viralai/dashboard/     # Phase 10: Development Dashboard
    collector.py                 # gathers real signals: plugins, models, benchmarks, docs
    builder.py                      # DashboardSnapshot + Markdown rendering

conftest.py                 # Phase 10: auto-marks tests by location for the test pyramid

docs/PLUGIN_DEVELOPMENT_STANDARD.md   # the contract every plugin must follow
```

## Design principles carried over from the Blueprint

- **Virus-independent Core Engine** — no biological knowledge lives here; that arrives via plugins in Phase 1.
- **Reproducibility by construction** — every object gets a UUID, timestamp, and version metadata automatically; you cannot opt out of provenance.
- **Configuration over hardcoding** — behavior is driven by config objects, not hardcoded logic.
- **Build correctly before building bigger** — Phase 0 has ~90%+ test coverage on purpose; this is the layer everything else depends on.

## Next phase

Phase 11 — Deployment: containerization (Docker/Kubernetes), the four-tier rollout
(Research Workstation → Laboratory → Institutional → Global Network) packaged as
installable artifacts from the start, and cloud-native deployment. This is also where
ADR-004's Event Bus/Task Scheduler in-process decision and ADR-012's encryption
key-management gap both get revisited, since real multi-process/multi-user deployment is
exactly their documented trigger.
