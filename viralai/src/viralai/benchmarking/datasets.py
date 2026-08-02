"""
Synthetic benchmark datasets (Ch.33.4's "synthetic datasets" category).

Every dataset here is constructed, not observed -- the ground truth is exactly correct
by construction, which is what benchmark datasets are for: proving the engines compute
the RIGHT answer on cases where we already know what right looks like. This says nothing
about biological realism (these are not real viral sequences), only about engine
correctness -- see ADR-013 and the module docstring in benchmarking/models.py.
"""

from __future__ import annotations

from viralai.benchmarking.models import BenchmarkDataset

# Same "ATGCAATAA" (M-Q-stop) fixture gene used across Phase 2-9 tests, kept consistent
# so a benchmark failure is easy to cross-reference against known-good unit test behavior.
_SIMPLE_GENE_REFERENCE = "ATGCAATAA"
_SIMPLE_GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


def mutation_detection_datasets() -> list[BenchmarkDataset]:
    """Reference/query pairs with a known, exact set of injected mutation positions."""
    return [
        BenchmarkDataset(
            name="single-substitution",
            category="mutation_detection",
            virus="synthetic",
            is_synthetic=True,
            reference_genome=_SIMPLE_GENE_REFERENCE,
            query_genome="ATGCTATAA",  # single substitution at position 4
            expected_mutation_positions=[4],
            expected_mutation_count=1,
            notes="One missense substitution, matches Phase 2's protein engine test fixture.",
        ),
        BenchmarkDataset(
            name="no-mutations",
            category="mutation_detection",
            virus="synthetic",
            is_synthetic=True,
            reference_genome=_SIMPLE_GENE_REFERENCE,
            query_genome=_SIMPLE_GENE_REFERENCE,
            expected_mutation_positions=[],
            expected_mutation_count=0,
            notes="Identical sequences -- correctness check for the zero-mutation case.",
        ),
        BenchmarkDataset(
            name="multiple-substitutions",
            category="mutation_detection",
            virus="synthetic",
            is_synthetic=True,
            reference_genome="AAAAAAAAAA",
            query_genome="ATAATAATAA",
            expected_mutation_positions=[1, 4, 7],
            expected_mutation_count=3,
            notes="Three independent substitutions at known positions.",
        ),
        BenchmarkDataset(
            name="single-deletion",
            category="mutation_detection",
            virus="synthetic",
            is_synthetic=True,
            reference_genome="ACGTACGT",
            query_genome="ACGTCGT",  # one base deleted
            expected_mutation_count=1,
            notes="Tests the alignment-based (unequal-length) detection path from ADR-005.",
        ),
    ]


def protein_classification_datasets() -> list[BenchmarkDataset]:
    """Mutations with known, hand-verified protein-level classifications (the same
    codon math worked out by hand in Phase 2's test suite).
    """
    return [
        BenchmarkDataset(
            name="missense-substitution",
            category="protein_classification",
            virus="synthetic",
            is_synthetic=True,
            reference_genome=_SIMPLE_GENE_REFERENCE,
            query_genome="ATGCTATAA",
            gene_annotations=_SIMPLE_GENE_ANNOTATIONS,
            expected_details={
                "position": 4,
                "classification": "missense",
                "reference_aa": "Q",
                "observed_aa": "L",
            },
        ),
        BenchmarkDataset(
            name="synonymous-substitution",
            category="protein_classification",
            virus="synthetic",
            is_synthetic=True,
            reference_genome=_SIMPLE_GENE_REFERENCE,
            query_genome="ATGCAGTAA",
            gene_annotations=_SIMPLE_GENE_ANNOTATIONS,
            expected_details={
                "position": 5,
                "classification": "synonymous",
                "reference_aa": "Q",
                "observed_aa": "Q",
            },
        ),
        BenchmarkDataset(
            name="nonsense-substitution",
            category="protein_classification",
            virus="synthetic",
            is_synthetic=True,
            reference_genome=_SIMPLE_GENE_REFERENCE,
            query_genome="ATGTAATAA",
            gene_annotations=_SIMPLE_GENE_ANNOTATIONS,
            expected_details={
                "position": 3,
                "classification": "nonsense",
                "reference_aa": "Q",
                "observed_aa": "*",
            },
        ),
    ]


def all_benchmark_datasets() -> list[BenchmarkDataset]:
    return mutation_detection_datasets() + protein_classification_datasets()
