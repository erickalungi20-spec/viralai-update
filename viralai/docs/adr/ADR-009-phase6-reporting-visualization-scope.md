# ADR-009: Phase 6 export format and visualization scope

## Status
Accepted

## Context
Blueprint Ch.19.5 specifies report export to PDF, HTML, Markdown, CSV, Excel, JSON, and
interactive dashboards (labeled "future" in the blueprint itself). Ch.28 specifies a
Visualization Engine including 3D/VR genome exploration and real-time streaming
visualizations (also explicitly "future" in the blueprint).

## Decisions

1. **Markdown, JSON, CSV, and HTML export are implemented now; PDF and Excel are not.**
   The first four are achievable with the standard library plus dependencies already in
   the project (no new dependency at all). PDF needs a rendering library (reportlab or
   weasyprint) and Excel needs openpyxl -- both real, installable dependencies, but they
   add weight for formats that don't carry substance the other four don't already cover.
   This is a different judgment call than the Environmental Simulator (Phase 5) or Model
   Registry (Phase 4), which were "future" components built now because they were cheap
   and structurally important. PDF/Excel export are neither cheap nor structurally
   load-bearing for anything else in the system -- they're genuinely just additional
   output formats.

2. **Visualization produces static PNG figures via matplotlib, not interactive
   dashboards.** The blueprint itself lists interactive dashboards, VR exploration, and
   real-time streaming as future directions (Ch.28.6), distinct from the "future"
   components elsewhere (like the Environmental Simulator) that were realistic to build
   immediately. An interactive dashboard needs a UI to be interactive *in* -- that
   infrastructure doesn't exist until Phase 8 (API layer) at the earliest, so building
   "interactivity" now would mean building against infrastructure that doesn't exist,
   the same category of mistake ADR-004 already reasoned through for the Event Bus.
   Static publication-quality figures (genome mutation map, diversity trend, feature
   importance) are fully implemented and give real value today.

3. **Visualization data preparation is separated from rendering.**
   `visualization/plot_data.py` has no matplotlib dependency at all -- it produces plain
   dataclasses. `visualization/figures.py` is the only module that imports matplotlib.
   This means the same prepared data can later feed a Phase 8 API response (JSON) or an
   interactive frontend chart library, without `plot_data.py` needing to change when the
   rendering story changes.

4. **The Automated Documentation Engine introspects real code, it doesn't generate
   placeholder documentation.** `api_reference.py` uses `inspect`/`pkgutil` against the
   actual installed package -- if a public class or function has no docstring, it's
   listed under "Documentation gaps" rather than silently skipped or backfilled with
   invented text. `dependency_graph.py` parses real import statements via `ast` (no code
   execution) and can detect real circular dependencies via `networkx.simple_cycles` --
   both are genuine static analysis tools, not documentation theater.

## Consequences
- **Positive:** every export format and every visualization claim in this phase is fully
  implemented and tested -- no partial stubs.
- **Positive:** the Documentation Engine can be run against the actual `viralai` package
  today and will report real documentation gaps, which is more useful than a manually
  maintained doc set that silently drifts from the code.
- **Negative:** researchers wanting PDF/Excel output must convert from Markdown/CSV
  externally for now (e.g. pandoc for PDF, importing the CSV into a spreadsheet tool).
- **Negative:** no interactive genome browser exists yet -- all visualization is static
  images meant for embedding in reports or notebooks, not click-to-explore interfaces.

## Trigger for revisiting
- PDF/Excel: the first time a grant application or institutional customer specifically
  requires one of these formats and Markdown/CSV genuinely isn't sufficient.
- Interactive dashboards: once Phase 8's API layer exists to serve an actual frontend.
