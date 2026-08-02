"""
Benchmark Repository models (Blueprint Ch.33: "Benchmark Repository shall maintain
curated benchmark datasets representing HPV, HIV, SARS-CoV-2, Influenza, synthetic
datasets, and future supported viruses").

Scope decision, stated honestly (see ADR-013): this repository ships with SYNTHETIC
benchmark datasets only. Real per-virus benchmark datasets (actual HPV/HIV/SARS-CoV-2/
Influenza sequences with known, published ground-truth mutations) require the same real
reference data this project has consistently declined to fabricate or commit without a
verifiable source (see plugins/hpv16/data/reference/README.md's policy). The synthetic
datasets here have KNOWN, exactly-correct ground truth by construction (we generated the
mutations, so we know exactly what they are) -- which is precisely what makes them useful
for validating engine correctness, even though they say nothing about real-world
biological accuracy. Real per-virus benchmarks are a documented, awaited addition once
real reference genomes are provisioned.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from viralai.common.ids import new_id
from viralai.core.idm import Genome


class BenchmarkDataset(BaseModel):
    """A benchmark case: an input plus its known-correct expected output."""

    dataset_id: str = Field(default_factory=lambda: new_id("benchmark-dataset"))
    name: str
    category: str  # "mutation_detection", "protein_classification", "ai_prediction"
    virus: str  # e.g. "synthetic", or a real virus name once real benchmarks exist
    is_synthetic: bool
    reference_genome: str | Genome
    query_genome: str | Genome | None = None
    gene_annotations: list[dict] = Field(default_factory=list)
    expected_mutation_positions: list[int] = Field(default_factory=list)
    expected_mutation_count: int | None = None
    expected_details: dict = Field(default_factory=dict)
    notes: str = ""


class BenchmarkMetric(BaseModel):
    metric_name: str
    expected: float
    actual: float
    tolerance: float
    passed: bool


class BenchmarkResult(BaseModel):
    result_id: str = Field(default_factory=lambda: new_id("benchmark-result"))
    dataset_id: str
    dataset_name: str
    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    software_version: str
    metrics: list[BenchmarkMetric] = Field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(m.passed for m in self.metrics)
