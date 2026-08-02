# Architecture Review & Implementation Plan

Summary
-------
This document records a quick architectural review of the Phase 0 foundation and a pragmatic plan
to advance the project toward Phase 4+ (AI engine, training pipeline, model registry) and beyond.

High-level observations
-----------------------
- Clean modular layout following phased scope (core, plugins, engines, AI, simulation, API).
- Strong emphasis on provenance, reproducibility, and a test-heavy foundation (conftest auto-marking).
- AI surface (src/viralai/ai) is scoped for feature extraction, model registry, explainability, and a
  training pipeline manager.

Short-term goals (next milestone)
---------------------------------
1. Solidify AI package surface area and backwards-compatible exports.
2. Add lightweight CI checks that run fast unit tests and import-smoke checks (no heavy GPU or data).
3. Create a minimal ModelRegistry backend (file-backed) with clear serialization/versioning.
4. Add one end-to-end training pipeline smoke integration using a tiny synthetic dataset.
5. Document plugin contract expectations for AI-relevant plugins (feature sources, reference data).

Implementation tasks (first sprint)
----------------------------------
- Draft design doc describing `ModelRegistry` storage format and discovery API (JSON+manifest).
- Add an import-discovery smoke test for `viralai.ai` (quick CI guard against obvious import regressions).
- Add a small `docs/ARCHITECTURE_PLAN.md` (this file) and link to relevant ADRs in `docs/adr/`.
- Scaffold `src/viralai/ai/registry.py` improvements (atomic file writes, versioning).  

Risks and constraints
---------------------
- Heavy ML deps (scikit-learn, SHAP, numba) make import-time checks brittle in CI; prefer discovery tests
  and small isolated unit tests mocking heavy behavior.
- Real benchmark datasets are intentionally external; use synthetic data for early training pipeline tests.

Next steps (I'll start these now)
--------------------------------
1. Add the import-discovery smoke test to `tests/ai/`.
2. Draft `docs/ARCHITECTURE_PLAN.md` (this file).
3. Begin scaffolding `ModelRegistry` improvements and a small example trainer.

Reference ADRs
--------------
- docs/adr/ADR-004-phase0-pragmatic-infrastructure.md
- docs/adr/ADR-013-phase10-testing-benchmarking-scope.md
