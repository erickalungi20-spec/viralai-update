"""
Dataset registry and training dataset validation.

Phase 4's training pipeline is deliberate: datasets are imported, validated,
and then used to train an AI model through a tracked pipeline. This module is a
small file-backed dataset repository supporting that flow.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from viralai.ai.features import FeatureContext
from viralai.ai.training_pipeline import LabeledExample
from viralai.common.errors import ValidationError
from viralai.common.ids import new_id
from viralai.core.idm import Mutation

_ALLOWED_CONTEXT_KEYS = {"genome_length", "entropy_at_position", "population_frequency"}


class DatasetExample(BaseModel):
    mutation: Mutation
    context: dict[str, float] = Field(default_factory=dict)
    label: int = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_context(self) -> "DatasetExample":
        context = dict(self.context or {})
        if "genome_length" not in context:
            raise ValueError("Dataset example context must include genome_length")

        genome_length = int(context["genome_length"])
        if genome_length <= 0:
            raise ValueError("genome_length must be a positive integer")
        if self.mutation.position >= genome_length:
            raise ValueError("mutation.position must be less than genome_length")

        entropy_at_position = float(context.get("entropy_at_position", 0.0))
        if entropy_at_position < 0.0:
            raise ValueError("entropy_at_position must be non-negative")

        population_frequency = float(context.get("population_frequency", 0.0))
        if not (0.0 <= population_frequency <= 1.0):
            raise ValueError("population_frequency must be between 0.0 and 1.0")

        if extra_keys := set(self.context) - _ALLOWED_CONTEXT_KEYS:
            raise ValueError(f"Unsupported context keys: {sorted(extra_keys)}")

        self.context = {
            "genome_length": genome_length,
            "entropy_at_position": entropy_at_position,
            "population_frequency": population_frequency,
        }
        return self

    def as_labeled_example(self) -> LabeledExample:
        return LabeledExample(
            mutation=self.mutation,
            context=FeatureContext(
                genome_length=self.context["genome_length"],
                entropy_at_position=self.context["entropy_at_position"],
                population_frequency=self.context["population_frequency"],
            ),
            label=self.label,
        )


class TrainingDatasetRecord(BaseModel):
    name: str
    version: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    training_examples: list[DatasetExample]
    validation_examples: list[DatasetExample] = Field(default_factory=list)
    validation_split: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_count: int = 0
    validation_count: int = 0

    @model_validator(mode="after")
    def finalize_counts(self) -> "TrainingDatasetRecord":
        if not self.training_examples and not self.validation_examples:
            raise ValueError("A dataset must contain at least one example")
        self.sample_count = len(self.training_examples)
        self.validation_count = len(self.validation_examples)
        return self

    def all_examples(self) -> list[DatasetExample]:
        return list(self.training_examples) + list(self.validation_examples)

    def training_examples_as_labeled(self) -> list[LabeledExample]:
        return [example.as_labeled_example() for example in self.training_examples]

    def validation_examples_as_labeled(self) -> list[LabeledExample]:
        return [example.as_labeled_example() for example in self.validation_examples]


class DatasetRepository:
    def __init__(self, storage_dir: Path | str) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        *,
        name: str,
        version: str,
        description: str = "",
        training_examples: list[DatasetExample],
        validation_examples: list[DatasetExample] | None = None,
        validation_split: float = 0.0,
    ) -> TrainingDatasetRecord:
        if not training_examples and not validation_examples:
            raise ValidationError("Cannot register a dataset without examples")

        dataset_dir = self._dataset_dir(name, version)
        if dataset_dir.exists():
            raise ValidationError(f"Dataset '{name}' version '{version}' is already registered")

        validation_examples = validation_examples or []
        record = TrainingDatasetRecord(
            name=name,
            version=version,
            description=description,
            training_examples=training_examples,
            validation_examples=validation_examples,
            validation_split=validation_split,
        )
        dataset_dir.mkdir(parents=True)
        (dataset_dir / "record.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get_record(self, name: str, version: str) -> TrainingDatasetRecord:
        record_path = self._dataset_dir(name, version) / "record.json"
        if not record_path.exists():
            raise ValidationError(f"No registered dataset '{name}' version '{version}'")
        return TrainingDatasetRecord(**json.loads(record_path.read_text(encoding="utf-8")))

    def list_versions(self, name: str) -> list[str]:
        name_dir = self._storage_dir / _safe(name)
        if not name_dir.exists():
            return []
        return sorted(p.name for p in name_dir.iterdir() if p.is_dir())

    def list_dataset_names(self) -> list[str]:
        if not self._storage_dir.exists():
            return []
        return sorted(p.name for p in self._storage_dir.iterdir() if p.is_dir())

    def _dataset_dir(self, name: str, version: str) -> Path:
        return self._storage_dir / _safe(name) / _safe(version)


def _safe(value: str) -> str:
    if not value or "/" in value or "\\" in value or ".." in value:
        raise ValidationError(f"Invalid dataset identifier: {value!r}")
    return value
