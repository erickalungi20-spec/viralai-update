"""
Dashboard builder: assembles a DashboardSnapshot from the collector functions, and
renders it to Markdown for a human (or a CI job summary) to read.
"""

from __future__ import annotations

from pathlib import Path

from viralai.ai.registry import ModelRegistry
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.dashboard.collector import (
    collect_benchmark_summary,
    collect_documentation_gap_count,
    collect_model_statuses,
    collect_module_statuses,
    collect_plugin_statuses,
    software_version,
)
from viralai.dashboard.models import DashboardSnapshot


def build_snapshot(
    *,
    plugins_dir: Path | str,
    model_registry: ModelRegistry,
    benchmark_repository: BenchmarkRepository,
    test_count: int | None = None,
    test_coverage_percent: float | None = None,
    include_documentation_gaps: bool = True,
) -> DashboardSnapshot:
    benchmark_total, benchmark_passing = collect_benchmark_summary(benchmark_repository)

    return DashboardSnapshot(
        software_version=software_version(),
        modules=collect_module_statuses(),
        test_count=test_count,
        test_coverage_percent=test_coverage_percent,
        plugins=collect_plugin_statuses(plugins_dir),
        models=collect_model_statuses(model_registry),
        benchmark_datasets_total=benchmark_total,
        benchmark_datasets_passing=benchmark_passing,
        documentation_gap_count=(
            collect_documentation_gap_count() if include_documentation_gaps else None
        ),
    )


def to_markdown(snapshot: DashboardSnapshot) -> str:
    lines: list[str] = [
        "# ViralAI Development Dashboard",
        "",
        f"Generated: {snapshot.generated_at.isoformat()}  ",
        f"Software version: {snapshot.software_version}  ",
        f"**Release ready: {'YES' if snapshot.release_ready else 'NO'}**",
        "",
        "## Module Completion",
        "",
        f"{snapshot.modules_complete_count}/{len(snapshot.modules)} phases complete",
        "",
    ]
    for module in snapshot.modules:
        checkbox = "x" if module.complete else " "
        lines.append(f"- [{checkbox}] Phase {module.phase}: {module.name}")
    lines.append("")

    if snapshot.test_count is not None or snapshot.test_coverage_percent is not None:
        lines += ["## Test Suite", ""]
        if snapshot.test_count is not None:
            lines.append(f"- Tests: {snapshot.test_count}")
        if snapshot.test_coverage_percent is not None:
            lines.append(f"- Coverage: {snapshot.test_coverage_percent:.2f}%")
        lines.append("")

    lines += ["## Plugins", ""]
    if snapshot.plugins:
        lines.append("| Name | Version | Certification | Security Scan |")
        lines.append("|---|---|---|---|")
        for plugin in snapshot.plugins:
            scan_status = "clean" if plugin.security_scan_clean else "FINDINGS"
            lines.append(
                f"| {plugin.name} | {plugin.version} | {plugin.certification_tier} | {scan_status} |"
            )
    else:
        lines.append("No plugins found.")
    lines.append("")

    lines += ["## AI Models", ""]
    if snapshot.models:
        for model in snapshot.models:
            metrics_str = ", ".join(f"{k}={v:.3f}" for k, v in model.latest_metrics.items())
            lines.append(f"- **{model.name}** v{model.version} -- {metrics_str}")
    else:
        lines.append("No models registered.")
    lines.append("")

    lines += ["## Benchmarks", ""]
    lines.append(
        f"{snapshot.benchmark_datasets_passing}/{snapshot.benchmark_datasets_total} datasets passing"
    )
    lines.append("")

    if snapshot.documentation_gap_count is not None:
        lines += [
            "## Documentation",
            "",
            f"{snapshot.documentation_gap_count} public members without a docstring",
            "",
        ]

    return "\n".join(lines)
