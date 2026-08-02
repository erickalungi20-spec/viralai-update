import json
from pathlib import Path

import numpy as np

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.registry import ModelRegistry
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.dashboard.collector import (
    MODULE_PHASES,
    collect_benchmark_summary,
    collect_documentation_gap_count,
    collect_model_statuses,
    collect_module_statuses,
    collect_plugin_statuses,
)


def _write_manifest(plugin_dir: Path, **overrides) -> None:
    manifest = {
        "name": plugin_dir.name,
        "version": "0.1.0",
        "supported_viruses": ["FixtureVirus"],
        "compatible_core_engine_versions": "*",
        "authors": ["Test"],
        "license": "Apache-2.0",
        "reference_genome_citations": ["Fixture Citation"],
    }
    manifest.update(overrides)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))


def test_collect_module_statuses_defaults_to_all_complete():
    statuses = collect_module_statuses()
    assert len(statuses) == len(MODULE_PHASES)
    assert all(s.complete for s in statuses)


def test_collect_module_statuses_respects_explicit_completed_set():
    statuses = collect_module_statuses(completed_phases={0, 1})
    complete_phases = {s.phase for s in statuses if s.complete}
    assert complete_phases == {0, 1}


def test_collect_plugin_statuses_clean_plugin(tmp_path):
    plugin_dir = tmp_path / "clean-plugin"
    _write_manifest(plugin_dir)
    (plugin_dir / "__init__.py").write_text("x = 1\n")

    statuses = collect_plugin_statuses(tmp_path)

    assert len(statuses) == 1
    assert statuses[0].security_scan_clean is True


def test_collect_plugin_statuses_dirty_plugin(tmp_path):
    plugin_dir = tmp_path / "dirty-plugin"
    _write_manifest(plugin_dir)
    (plugin_dir / "__init__.py").write_text("eval('1')\n")

    statuses = collect_plugin_statuses(tmp_path)

    assert statuses[0].security_scan_clean is False


def test_collect_plugin_statuses_on_real_hpv16_plugin():
    real_plugins_dir = Path(__file__).resolve().parents[2] / "plugins"
    statuses = collect_plugin_statuses(real_plugins_dir)

    hpv16 = next(s for s in statuses if s.name == "hpv16")
    assert hpv16.security_scan_clean is True
    assert hpv16.certification_tier == "experimental"


def test_collect_model_statuses(tmp_path):
    registry = ModelRegistry(tmp_path)
    rng = np.random.RandomState(0)
    X = rng.rand(30, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    metrics = model.train(X, y)
    registry.register(
        model,
        name="test-model",
        version="0.1.0",
        training_metrics=metrics,
        training_sample_count=30,
    )

    statuses = collect_model_statuses(registry)

    assert len(statuses) == 1
    assert statuses[0].name == "test-model"
    assert "train_accuracy" in statuses[0].latest_metrics


def test_collect_model_statuses_empty_registry(tmp_path):
    registry = ModelRegistry(tmp_path)
    assert collect_model_statuses(registry) == []


def test_collect_benchmark_summary(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")
    repo.run_and_record()

    total, passing = collect_benchmark_summary(repo)

    assert total > 0
    assert passing == total


def test_collect_benchmark_summary_no_runs_yet(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")
    total, passing = collect_benchmark_summary(repo)
    assert (total, passing) == (0, 0)


def test_collect_documentation_gap_count_is_a_real_measurement():
    """Not asserting a specific number (that would make the test brittle against
    future docstring additions) -- just that it returns a real, non-negative count."""
    count = collect_documentation_gap_count()
    assert isinstance(count, int)
    assert count >= 0
