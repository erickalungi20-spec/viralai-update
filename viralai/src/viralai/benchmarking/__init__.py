"""
Phase 10 Benchmark Repository (Ch.33) + Reproducibility Testing (Ch.32.5).

Synthetic benchmark datasets with known-by-construction ground truth (real per-virus
benchmarks await real reference genomes -- see ADR-013), a runner that scores engines
against them, a repository storing run history over time, and a reusable reproducibility
check harness.
"""

from viralai.benchmarking.datasets import all_benchmark_datasets
from viralai.benchmarking.models import BenchmarkDataset, BenchmarkMetric, BenchmarkResult
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.benchmarking.reproducibility import (
    ReproducibilityReport,
    assert_reproducible,
    check_reproducibility,
)
from viralai.benchmarking.runner import (
    run_all_benchmarks,
    run_mutation_detection_benchmark,
    run_protein_classification_benchmark,
)

__all__ = [
    "BenchmarkDataset",
    "BenchmarkMetric",
    "BenchmarkResult",
    "all_benchmark_datasets",
    "run_all_benchmarks",
    "run_mutation_detection_benchmark",
    "run_protein_classification_benchmark",
    "BenchmarkRepository",
    "ReproducibilityReport",
    "check_reproducibility",
    "assert_reproducible",
]
