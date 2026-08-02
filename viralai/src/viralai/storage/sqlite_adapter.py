from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List

import joblib
from pydantic import BaseModel

from viralai.ai.hotspot_model import DeepMutationModel, MutationHotspotModel
from viralai.ai.registry import ModelRecord as PydanticModelRecord
from viralai.common.errors import ValidationError


@dataclass
class ModelRow:
    name: str
    version: str
    registered_at: str
    training_metrics: str
    feature_names: str
    training_sample_count: int
    notes: str
    model_blob: bytes


class SQLiteModelRegistry:
    """A lightweight SQLite-backed registry for local durable metadata storage.

    Not intended as a full production Postgres replacement, but serves as a
    durable adapter for single-node deployments and to demonstrate a DB-backed
    registry backend.
    """

    def __init__(self, storage_dir: Path | str) -> None:
        self._db_path = Path(storage_dir) / "models.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS models (
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                training_metrics TEXT,
                feature_names TEXT,
                training_sample_count INTEGER,
                model_type TEXT,
                notes TEXT,
                model_blob BLOB,
                PRIMARY KEY (name, version)
            )
            """
        )
        self._conn.commit()

    def register(self, model: MutationHotspotModel, *, name: str, version: str, training_metrics: dict, training_sample_count: int, notes: str = "") -> PydanticModelRecord:
        if not model.is_trained:
            raise ValidationError("Cannot register an untrained model")

        # serialize sklearn model to bytes
        bio = BytesIO()
        joblib.dump(model.sklearn_model, bio)
        blob = bio.getvalue()

        registered_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO models (name, version, registered_at, training_metrics, feature_names, training_sample_count, model_type, notes, model_blob) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                version,
                registered_at,
                json.dumps(training_metrics),
                json.dumps(list(model.feature_importances().keys())) if model.is_trained else json.dumps([]),
                training_sample_count,
                model.model_type,
                notes,
                blob,
            ),
        )
        self._conn.commit()
        return PydanticModelRecord(
            name=name,
            version=version,
            registered_at=registered_at,
            training_metrics=training_metrics,
            feature_names=list(),
            training_sample_count=training_sample_count,
            model_type=model.model_type,
            notes=notes,
        )

    def get_record(self, name: str, version: str) -> PydanticModelRecord:
        cur = self._conn.execute(
            "SELECT registered_at, training_metrics, feature_names, training_sample_count, model_type, notes FROM models WHERE name=? AND version=?",
            (name, version),
        )
        row = cur.fetchone()
        if not row:
            raise ValidationError(f"No registered model '{name}' version '{version}'")
        registered_at, training_metrics, feature_names, training_sample_count, model_type, notes = row
        return PydanticModelRecord(
            name=name,
            version=version,
            registered_at=registered_at,
            training_metrics=json.loads(training_metrics) if training_metrics else {},
            feature_names=json.loads(feature_names) if feature_names else [],
            training_sample_count=training_sample_count,
            model_type=model_type or "",
            notes=notes or "",
        )

    def load_model(self, name: str, version: str) -> MutationHotspotModel:
        cur = self._conn.execute(
            "SELECT model_blob, model_type FROM models WHERE name=? AND version=?", (name, version)
        )
        row = cur.fetchone()
        if not row:
            raise ValidationError(f"No registered model '{name}' version '{version}'")
        blob, model_type = row
        bio = BytesIO(blob)
        sklearn_model = joblib.load(bio)

        if model_type == "deep_neural_network":
            wrapper = DeepMutationModel()
        else:
            wrapper = MutationHotspotModel()
        wrapper._model = sklearn_model
        wrapper._is_trained = True
        return wrapper

    def list_versions(self, name: str) -> List[str]:
        cur = self._conn.execute("SELECT version FROM models WHERE name=?", (name,))
        return [r[0] for r in cur.fetchall()]

    def list_model_names(self) -> List[str]:
        cur = self._conn.execute("SELECT DISTINCT name FROM models")
        return [r[0] for r in cur.fetchall()]

    def latest_version(self, name: str) -> str | None:
        cur = self._conn.execute("SELECT version, registered_at FROM models WHERE name=?", (name,))
        rows = cur.fetchall()
        if not rows:
            return None
        rows.sort(key=lambda r: r[1])
        return rows[-1][0]
