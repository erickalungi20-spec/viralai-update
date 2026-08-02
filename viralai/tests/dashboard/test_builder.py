from pathlib import Path

from viralai.ai.registry import ModelRegistry
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.dashboard.builder import build_snapshot, to_markdown


def test_build_snapshot_against_real_plugins_dir(tmp_path):
    real_plugins_dir = Path(__file__).resolve().parents[2] / "plugins"
    registry = ModelRegistry(tmp_path / "models")
    benchmarks = BenchmarkRepository(tmp_path / "benchmarks.json")
    benchmarks.run_and_record()

    snapshot = build_snapshot(
        plugins_dir=real_plugins_dir, model_registry=registry, benchmark_repository=benchmarks
    )

    assert snapshot.software_version
    assert len(snapshot.modules) > 0
    assert any(p.name == "hpv16" for p in snapshot.plugins)
    assert snapshot.benchmark_datasets_total > 0
    assert snapshot.benchmark_datasets_passing == snapshot.benchmark_datasets_total


def test_to_markdown_contains_key_sections(tmp_path):
    real_plugins_dir = Path(__file__).resolve().parents[2] / "plugins"
    registry = ModelRegistry(tmp_path / "models")
    benchmarks = BenchmarkRepository(tmp_path / "benchmarks.json")
    benchmarks.run_and_record()

    snapshot = build_snapshot(
        plugins_dir=real_plugins_dir, model_registry=registry, benchmark_repository=benchmarks
    )
    markdown = to_markdown(snapshot)

    assert "# ViralAI Development Dashboard" in markdown
    assert "## Module Completion" in markdown
    assert "## Plugins" in markdown
    assert "## AI Models" in markdown
    assert "## Benchmarks" in markdown
    assert "hpv16" in markdown


def test_to_markdown_shows_release_ready_status(tmp_path):
    real_plugins_dir = Path(__file__).resolve().parents[2] / "plugins"
    registry = ModelRegistry(tmp_path / "models")
    benchmarks = BenchmarkRepository(tmp_path / "benchmarks.json")
    benchmarks.run_and_record()

    snapshot = build_snapshot(
        plugins_dir=real_plugins_dir, model_registry=registry, benchmark_repository=benchmarks
    )
    markdown = to_markdown(snapshot)

    assert "Release ready: YES" in markdown or "Release ready: NO" in markdown


def test_build_snapshot_with_no_benchmarks_run_yet(tmp_path):
    empty_plugins_dir = tmp_path / "no-plugins"
    empty_plugins_dir.mkdir()
    registry = ModelRegistry(tmp_path / "models")
    benchmarks = BenchmarkRepository(tmp_path / "benchmarks.json")

    snapshot = build_snapshot(
        plugins_dir=empty_plugins_dir, model_registry=registry, benchmark_repository=benchmarks
    )

    assert snapshot.benchmark_datasets_total == 0
    assert snapshot.plugins == []


def test_build_snapshot_with_test_metrics_provided(tmp_path):
    empty_plugins_dir = tmp_path / "no-plugins"
    empty_plugins_dir.mkdir()
    registry = ModelRegistry(tmp_path / "models")
    benchmarks = BenchmarkRepository(tmp_path / "benchmarks.json")

    snapshot = build_snapshot(
        plugins_dir=empty_plugins_dir,
        model_registry=registry,
        benchmark_repository=benchmarks,
        test_count=396,
        test_coverage_percent=98.39,
    )
    markdown = to_markdown(snapshot)

    assert "Tests: 396" in markdown
    assert "98.39%" in markdown
