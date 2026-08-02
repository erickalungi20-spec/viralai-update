import pytest

from viralai.benchmarking.datasets import (
    all_benchmark_datasets,
    mutation_detection_datasets,
    protein_classification_datasets,
)
from viralai.benchmarking.models import BenchmarkDataset
from viralai.benchmarking.runner import (
    run_all_benchmarks,
    run_mutation_detection_benchmark,
    run_protein_classification_benchmark,
)
from viralai.core.idm import Genome


def test_all_mutation_detection_benchmarks_pass():
    for dataset in mutation_detection_datasets():
        result = run_mutation_detection_benchmark(dataset)
        assert result.all_passed, f"{dataset.name} failed: {result.metrics}"


def test_all_protein_classification_benchmarks_pass():
    for dataset in protein_classification_datasets():
        result = run_protein_classification_benchmark(dataset)
        assert result.all_passed, f"{dataset.name} failed: {result.metrics}"


def test_run_all_benchmarks_covers_every_dataset():
    datasets = all_benchmark_datasets()
    results = run_all_benchmarks(datasets)

    assert len(results) == len(datasets)
    assert all(r.all_passed for r in results)


def test_benchmark_runner_accepts_genome_objects():
    reference = Genome(genome_id="ref", virus_species="synthetic", sequence="ACGT")
    query = Genome(genome_id="query", virus_species="synthetic", sequence="ACGA")
    dataset = BenchmarkDataset(
        name="genome-object-case",
        category="mutation_detection",
        virus="synthetic",
        is_synthetic=True,
        reference_genome=reference,
        query_genome=query,
        expected_mutation_count=1,
    )

    result = run_mutation_detection_benchmark(dataset)

    assert result.all_passed is True
    assert result.metrics[0].metric_name == "mutation_count"
    assert result.metrics[0].actual == 1


def test_mutation_count_metric_fails_when_wrong():
    bad_dataset = BenchmarkDataset(
        name="deliberately-wrong",
        category="mutation_detection",
        virus="synthetic",
        is_synthetic=True,
        reference_genome="ACGT",
        query_genome="ACGT",
        expected_mutation_count=5,  # wrong -- identical sequences have 0 mutations
    )

    result = run_mutation_detection_benchmark(bad_dataset)

    assert result.all_passed is False


def test_all_datasets_are_marked_synthetic():
    for dataset in all_benchmark_datasets():
        assert dataset.is_synthetic is True


def test_wrong_category_raises():
    wrong_category = BenchmarkDataset(
        name="x",
        category="protein_classification",
        virus="synthetic",
        is_synthetic=True,
        reference_genome="ACGT",
    )
    with pytest.raises(ValueError):
        run_mutation_detection_benchmark(wrong_category)
