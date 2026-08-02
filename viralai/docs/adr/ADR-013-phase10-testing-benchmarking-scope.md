# ADR-013: Phase 10 scope -- synthetic benchmark datasets, auto-marked test pyramid

## Status
Accepted

## Context
Blueprint Ch.32 (Testing Framework), Ch.33 (Benchmarking), Ch.34 (Sci-CI), and the
engineering review's Recommendation 10 (Development Dashboard) call for a full test
pyramid, a curated benchmark repository across named viruses, reproducibility testing,
a Sci-CI gate, and a development status dashboard.

## Decisions

1. **Benchmark Repository ships with synthetic datasets only, not real per-virus
   benchmarks.** Ch.33.4 names HPV/HIV/SARS-CoV-2/Influenza specifically, but real
   benchmark datasets need real reference sequences with published, verifiable ground
   truth -- exactly the kind of data this project has consistently declined to fabricate
   or commit without a source (see the HPV16 plugin's reference genome policy from Phase
   1). The synthetic datasets here have exactly-correct ground truth *by construction*
   (the mutations were injected by the test author, so the correct answer is known with
   certainty) -- which validates engine correctness, but says nothing about real-world
   biological accuracy. Real per-virus benchmarks are a documented, awaited addition, not
   a gap being hidden.

2. **The test pyramid (Ch.32.3: unit/integration/system/plugin/performance) is made
   queryable via automatic marking, not by hand-annotating ~450 existing tests.** A root
   `conftest.py` classifies every collected test by its file location (plugin tests,
   performance tests, the two capstone "system" tests, anything with "integration" in
   its filename, everything else defaults to unit). This is a real, working
   classification (`pytest -m system` actually runs only the capstone tests) achieved
   without a large, low-value mechanical annotation pass, and it also means new tests
   get classified automatically by where they're placed.

3. **Reproducibility testing is a small, reusable, general-purpose harness, not
   duplicated per-module logic.** Phase 5 already proved simulation reproducibility via
   `DigitalLaboratoryManager.replay()`. `benchmarking/reproducibility.py` generalizes the
   same "run twice, compare exactly" check into `assert_reproducible()`, usable for any
   deterministic operation (mutation detection, AI prediction, simulation) -- both in
   tests and as an explicit Sci-CI gate step, not just an ad hoc pattern repeated per
   engine.

4. **The Sci-CI pipeline adds real, meaningful gates, not cosmetic steps.** Beyond
   lint/format/test-with-coverage (which already existed), CI now runs: system tests
   isolated as their own step (so a capstone failure is immediately visible, not buried
   in ~450 other results), the plugin security scanner from Phase 9 against every shipped
   plugin (a real Ch.35.4 gate, not just a local dev tool), the full benchmark suite with
   a nonzero exit code on any failing dataset, and an explicit reproducibility check. Each
   of these was manually verified to actually fail when it should before being wired into
   CI (see the runner-verification commands in this ADR's accompanying commit).

5. **The Development Dashboard measures real signals it can compute directly (plugin
   certification + security scan status, registered AI model metrics, benchmark
   pass/fail, live documentation-gap count from Phase 6's Documentation Engine) and
   accepts test coverage/count as an external input rather than re-running the test
   suite itself.** Measuring coverage requires a full pytest run; having the dashboard
   builder re-run that internally would mean either duplicating CI's test run or coupling
   the dashboard to a specific coverage report format. CI computes coverage once and can
   pass it in; the dashboard's own job (in this phase) is what it can measure without
   that dependency.

6. **`release_ready` is a conservative, explicit boolean, not a fuzzy score.** All
   tracked modules complete AND all plugin security scans clean AND (if benchmarks have
   run) all benchmarks passing. Coverage and documentation gaps are surfaced on the
   snapshot but don't gate this flag by themselves -- those are quality signals a human
   should weigh in context, not binary pass/fail conditions by nature.

## Consequences
- **Positive:** every Sci-CI gate added in this phase was manually run and verified to
  produce the correct pass/fail signal before being wired into the GitHub Actions
  workflow -- this isn't a workflow file written and hoped to work.
- **Positive:** `pytest -m plugin`, `pytest -m system`, `pytest -m performance` are now
  real, useful commands a developer can run locally to exercise one layer of the pyramid
  without running the full ~450-test suite.
- **Negative:** the benchmark suite's synthetic-only scope means a real biological
  regression (e.g. a subtly wrong codon table entry that happens not to be exercised by
  the current synthetic fixtures) would not necessarily be caught by "all benchmarks
  passing" -- the benchmark repository validates internal consistency, not biological
  ground truth, until real per-virus datasets exist.
- **Negative:** the auto-marking conftest.py's classification is a heuristic (path-based
  pattern matching), not a semantic analysis of what a test actually does -- a test that
  happens to touch two engines but isn't named with "integration" defaults to "unit".
  This is a reasonable approximation, not a perfect taxonomy.

## Trigger for revisiting
- Real per-virus benchmarks: once a real reference genome (e.g. HPV16's, per its own
  README) is provisioned and its true, published mutation/variant data can be sourced and
  cited, the same pattern used for synthetic datasets extends directly to a real one.
- Dashboard coverage self-measurement: if the dashboard needs to run standalone outside
  a CI context where a coverage report isn't already available.
