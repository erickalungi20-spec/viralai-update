"""
Model Registry (Blueprint Ch.26.3, Addition 17).

Every trained model is stored with its version, training metrics, feature schema, and
timestamp — never just a bare pickle file with no record of how it was produced. This is
the same "no developer should have to remember to add provenance" philosophy as Phase 0's
Metadata Engine, applied to models specifically.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from pydantic import BaseModel, Field

from viralai.ai.features import FEATURE_NAMES
from viralai.ai.hotspot_model import DeepMutationModel, MutationHotspotModel, MutationModelBase
from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger

logger = get_logger("ai.registry")


class ModelRecord(BaseModel):
    """Metadata stored alongside every registered model — the Model Registry's answer to
    "what is this model, how was it trained, and can I trust the number it just gave me".
    """

    name: str
    version: str
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    training_metrics: dict[str, float]
    feature_names: list[str]
    training_sample_count: int
    model_type: str
    notes: str = ""


class ModelRegistry:
    """File-backed model store: one subdirectory per (name, version), containing the
    serialized model (joblib) and its ModelRecord (JSON). Same pragmatic "real, tested,
    file-backed now, swap the backend later" pattern as the Knowledge Base.
    """

    def __init__(self, storage_dir: Path | str) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        model: MutationModelBase,
        *,
        name: str,
        version: str,
        training_metrics: dict[str, float],
        training_sample_count: int,
        notes: str = "",
    ) -> ModelRecord:
        if not model.is_trained:
            raise ValidationError("Cannot register an untrained model")

        record = ModelRecord(
            name=name,
            version=version,
            training_metrics=training_metrics,
            feature_names=list(FEATURE_NAMES),
            training_sample_count=training_sample_count,
            model_type=model.model_type,
            notes=notes,
        )

        model_dir = self._model_dir(name, version)
        if model_dir.exists():
            raise ValidationError(f"Model '{name}' version '{version}' is already registered")
        model_dir.mkdir(parents=True)

        joblib.dump(model.sklearn_model, model_dir / "model.joblib")
        (model_dir / "record.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")

        logger.info("model registered: %s v%s (%s)", name, version, training_metrics)
        return record

    def get_record(self, name: str, version: str) -> ModelRecord:
        record_path = self._model_dir(name, version) / "record.json"
        if not record_path.exists():
            raise ValidationError(f"No registered model '{name}' version '{version}'")
        return ModelRecord(**json.loads(record_path.read_text(encoding="utf-8")))

    def load_model(self, name: str, version: str) -> MutationModelBase:
        """Reconstruct a usable model wrapper from a registered version."""
        record = self.get_record(name, version)
        model_dir = self._model_dir(name, version)
        sklearn_model_path = model_dir / "model.joblib"
        if not sklearn_model_path.exists():
            raise ValidationError(f"No registered model '{name}' version '{version}'")

        sklearn_model = joblib.load(sklearn_model_path)
        if record.model_type == DeepMutationModel.model_type:
            wrapper = DeepMutationModel()
        else:
            wrapper = MutationHotspotModel()
        wrapper._model = sklearn_model
        wrapper._is_trained = True
        return wrapper

    def list_versions(self, name: str) -> list[str]:
        name_dir = self._storage_dir / _safe(name)
        if not name_dir.exists():
            return []
        return sorted(p.name for p in name_dir.iterdir() if p.is_dir())

    def list_model_names(self) -> list[str]:
        """All model names with at least one registered version. Additive convenience
        for tooling (e.g. the Development Dashboard) that needs to enumerate everything
        in the registry without already knowing the names up front.
        """
        if not self._storage_dir.exists():
            return []
        return sorted(p.name for p in self._storage_dir.iterdir() if p.is_dir())

    def latest_version(self, name: str) -> str | None:
        """Latest by registration timestamp, not by version-string sort order — version
        strings aren't guaranteed to sort correctly as plain strings (e.g. "0.9.0" vs
        "0.10.0").
        """
        versions = self.list_versions(name)
        if not versions:
            return None
        records = [(v, self.get_record(name, v)) for v in versions]
        records.sort(key=lambda pair: pair[1].registered_at)
        return records[-1][0]

    def _model_dir(self, name: str, version: str) -> Path:
        return self._storage_dir / _safe(name) / _safe(version)


def _safe(value: str) -> str:
    """Filesystem-safe path component. Deliberately strict — model/version names should
    be simple identifiers, not arbitrary strings.
    """
    if not value or "/" in value or "\\" in value or ".." in value:
        raise ValidationError(f"Invalid model/version identifier: {value!r}")
    return value
