"""
Benchmark Repository (Blueprint Ch.33.4): stores benchmark run history so results are
comparable across software versions over time, not just a one-off local check. Same
file-backed pattern as every other registry in this codebase.
"""

from __future__ import annotations

import json
from pathlib import Path

from viralai.benchmarking.datasets import all_benchmark_datasets
from viralai.benchmarking.models import BenchmarkResult
from viralai.benchmarking.runner import run_all_benchmarks
from viralai.common.logging import get_logger

logger = get_logger("benchmarking.repository")


class BenchmarkRepository:
    def __init__(self, storage_path: Path | str) -> None:
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def run_and_record(self) -> list[BenchmarkResult]:
        """Runs every registered benchmark dataset and appends the results to history."""
        results = run_all_benchmarks(all_benchmark_datasets())
        self._append(results)
        pass_count = sum(1 for r in results if r.all_passed)
        logger.info("benchmark run complete: %d/%d datasets passed", pass_count, len(results))
        return results

    def history(self) -> list[BenchmarkResult]:
        if not self._storage_path.exists():
            return []
        raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        return [BenchmarkResult(**item) for item in raw]

    def latest_run(self) -> list[BenchmarkResult]:
        """The most recent run's results (all results sharing the latest run_at
        timestamp among each dataset's most recent entry).
        """
        history = self.history()
        if not history:
            return []
        latest_by_dataset: dict[str, BenchmarkResult] = {}
        for result in history:
            existing = latest_by_dataset.get(result.dataset_id)
            if existing is None or result.run_at >= existing.run_at:
                latest_by_dataset[result.dataset_id] = result
        return list(latest_by_dataset.values())

    def all_currently_passing(self) -> bool:
        latest = self.latest_run()
        return bool(latest) and all(r.all_passed for r in latest)

    def _append(self, results: list[BenchmarkResult]) -> None:
        history = self.history()
        history.extend(results)
        self._storage_path.write_text(
            json.dumps([r.model_dump(mode="json") for r in history], indent=2), encoding="utf-8"
        )
