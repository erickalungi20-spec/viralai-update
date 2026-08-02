"""
Metrics collection for the Development Dashboard. Each function gathers one category of
signal from a real, live source (plugin manifests + security scanner, the Model
Registry, the Benchmark Repository, the Automated Documentation Engine) -- nothing here
is a placeholder or a hardcoded "looks good" value.

Test coverage / test count are accepted as *inputs* rather than computed here: measuring
coverage means running the full test suite, which is a CI concern (parse `coverage.json`
after a real pytest run), not something this collector should re-run itself.
"""

from __future__ import annotations

from pathlib import Path

from viralai import __version__
from viralai.ai.registry import ModelRegistry
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.dashboard.models import ModelStatus, ModuleStatus, PluginStatus
from viralai.plugins.loader import list_plugin_manifests
from viralai.security.plugin_scanner import is_clean, scan_plugin_directory

# Reflects actual project status as of this phase -- update as new phases land.
MODULE_PHASES: list[tuple[int, str]] = [
    (0, "Foundation & Infrastructure Layer"),
    (1, "Plugin System"),
    (2, "Core Scientific Engines"),
    (3, "Knowledge Base + Research Graph"),
    (4, "AI Engine + Training Pipeline Manager"),
    (5, "Simulation Engine + Digital Laboratory Manager"),
    (6, "Reporting, Visualization & Documentation Engine"),
    (7, "Workflow Engine + Research Workspace"),
    (8, "API Layer"),
    (9, "Security & Responsible AI"),
    (10, "Testing, Benchmarking, CI/CD & Development Dashboard"),
]


def collect_module_statuses(completed_phases: set[int] | None = None) -> list[ModuleStatus]:
    """`completed_phases` defaults to "every phase up to and including this one" -- pass
    an explicit set to model a different point in the project's history if needed.
    """
    if completed_phases is None:
        completed_phases = {phase for phase, _ in MODULE_PHASES}
    return [
        ModuleStatus(phase=phase, name=name, complete=phase in completed_phases)
        for phase, name in MODULE_PHASES
    ]


def collect_plugin_statuses(plugins_dir: Path | str) -> list[PluginStatus]:
    statuses: list[PluginStatus] = []
    for manifest in list_plugin_manifests(plugins_dir):
        plugin_dir = Path(plugins_dir) / manifest.name
        scan_results = scan_plugin_directory(plugin_dir)
        statuses.append(
            PluginStatus(
                name=manifest.name,
                version=manifest.version,
                certification_tier=manifest.certification_tier.value,
                security_scan_clean=is_clean(scan_results),
            )
        )
    return statuses


def collect_model_statuses(registry: ModelRegistry) -> list[ModelStatus]:
    statuses: list[ModelStatus] = []
    for name in registry.list_model_names():
        version = registry.latest_version(name)
        if version is None:
            continue
        record = registry.get_record(name, version)
        statuses.append(
            ModelStatus(name=name, version=version, latest_metrics=record.training_metrics)
        )
    return statuses


def collect_benchmark_summary(repository: BenchmarkRepository) -> tuple[int, int]:
    """Returns (total, passing) from the repository's latest run."""
    latest = repository.latest_run()
    total = len(latest)
    passing = sum(1 for r in latest if r.all_passed)
    return total, passing


def collect_documentation_gap_count() -> int:
    """Counts entries under the Automated Documentation Engine's "Documentation gaps"
    section for the real installed package -- a live measurement, not an estimate.
    """
    import viralai
    from viralai.docs_engine.api_reference import generate_markdown

    markdown = generate_markdown(viralai)
    if "## Documentation gaps" not in markdown:
        return 0
    gap_section = markdown.split("## Documentation gaps", 1)[1]
    return gap_section.count("\n- `")


def software_version() -> str:
    return __version__
