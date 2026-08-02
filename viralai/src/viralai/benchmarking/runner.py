"""
Benchmark Runner: executes the real Phase 2 engines against BenchmarkDatasets and
produces scored BenchmarkResults. This is what actually validates engine correctness
against known ground truth, not just "the code ran without raising."
"""

from __future__ import annotations

from viralai import __version__
from viralai.benchmarking.models import BenchmarkDataset, BenchmarkMetric, BenchmarkResult
from viralai.core.idm import Genome
from viralai.engines.mutation_engine import MutationEngine
from viralai.engines.protein_engine import ProteinAnalysisEngine


def run_mutation_detection_benchmark(
    dataset: BenchmarkDataset, engine: MutationEngine | None = None
) -> BenchmarkResult:
    if dataset.category != "mutation_detection":
        raise ValueError(
            f"Dataset '{dataset.name}' is category '{dataset.category}', not mutation_detection"
        )

    engine = engine or MutationEngine()
    mutations = engine.detect_mutations(
        _coerce_genome(dataset.reference_genome),
        _coerce_genome(dataset.query_genome or dataset.reference_genome),
    )

    metrics: list[BenchmarkMetric] = []

    if dataset.expected_mutation_count is not None:
        metrics.append(
            _exact_metric(
                "mutation_count", expected=dataset.expected_mutation_count, actual=len(mutations)
            )
        )

    if dataset.expected_mutation_positions:
        detected_positions = {m.position for m in mutations}
        expected_positions = set(dataset.expected_mutation_positions)
        precision = _safe_ratio(
            len(detected_positions & expected_positions), len(detected_positions)
        )
        recall = _safe_ratio(len(detected_positions & expected_positions), len(expected_positions))
        metrics.append(_exact_metric("position_precision", expected=1.0, actual=precision))
        metrics.append(_exact_metric("position_recall", expected=1.0, actual=recall))

    return BenchmarkResult(
        dataset_id=dataset.dataset_id,
        dataset_name=dataset.name,
        software_version=__version__,
        metrics=metrics,
    )


def run_protein_classification_benchmark(
    dataset: BenchmarkDataset,
    mutation_engine: MutationEngine | None = None,
    protein_engine: ProteinAnalysisEngine | None = None,
) -> BenchmarkResult:
    if dataset.category != "protein_classification":
        raise ValueError(
            f"Dataset '{dataset.name}' is category '{dataset.category}', not protein_classification"
        )

    mutation_engine = mutation_engine or MutationEngine()
    protein_engine = protein_engine or ProteinAnalysisEngine()

    mutations = mutation_engine.detect_mutations(
        _coerce_genome(dataset.reference_genome),
        _coerce_genome(dataset.query_genome or dataset.reference_genome),
    )
    protein_mutations = protein_engine.analyze(
        _coerce_genome(dataset.reference_genome), mutations, dataset.gene_annotations
    )

    expected_position = dataset.expected_details.get("position")
    matching = [pm for pm in protein_mutations if pm.source_mutation.position == expected_position]

    metrics: list[BenchmarkMetric] = []
    if matching:
        pm = matching[0]
        metrics.append(
            _exact_metric(
                "classification_correct",
                expected=1.0,
                actual=(
                    1.0
                    if pm.classification.value == dataset.expected_details.get("classification")
                    else 0.0
                ),
            )
        )
        metrics.append(
            _exact_metric(
                "observed_aa_correct",
                expected=1.0,
                actual=(
                    1.0 if pm.observed_aa == dataset.expected_details.get("observed_aa") else 0.0
                ),
            )
        )
    else:
        metrics.append(_exact_metric("classification_correct", expected=1.0, actual=0.0))

    return BenchmarkResult(
        dataset_id=dataset.dataset_id,
        dataset_name=dataset.name,
        software_version=__version__,
        metrics=metrics,
    )


def run_all_benchmarks(datasets: list[BenchmarkDataset]) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for dataset in datasets:
        if dataset.category == "mutation_detection":
            results.append(run_mutation_detection_benchmark(dataset))
        elif dataset.category == "protein_classification":
            results.append(run_protein_classification_benchmark(dataset))
        else:
            raise ValueError(f"No benchmark runner registered for category '{dataset.category}'")
    return results


def _exact_metric(
    name: str, *, expected: float, actual: float, tolerance: float = 1e-9
) -> BenchmarkMetric:
    return BenchmarkMetric(
        metric_name=name,
        expected=expected,
        actual=actual,
        tolerance=tolerance,
        passed=abs(expected - actual) <= tolerance,
    )


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator > 0 else 1.0


def _coerce_genome(value: str | Genome | None) -> str | Genome:
    if value is None:
        return ""
    return value
