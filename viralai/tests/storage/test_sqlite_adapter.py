import numpy as np
import pytest

from viralai.ai.hotspot_model import DeepMutationModel, MutationHotspotModel
from viralai.storage.sqlite_adapter import SQLiteModelRegistry
from viralai.common.errors import ValidationError


def _trained_rf_model() -> MutationHotspotModel:
    from numpy.random import RandomState

    rng = RandomState(0)
    X = rng.rand(30, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    model.train(X, y)
    return model


def _trained_deep_model() -> DeepMutationModel:
    from numpy.random import RandomState

    rng = RandomState(0)
    X = rng.rand(30, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = DeepMutationModel(max_iter=200)
    model.train(X, y)
    return model


def test_sqlite_registry_stores_and_loads_rf_model(tmp_path):
    registry = SQLiteModelRegistry(tmp_path)
    model = _trained_rf_model()
    record = registry.register(
        model,
        name="rf-model",
        version="0.1.0",
        training_metrics={"train_accuracy": 0.85},
        training_sample_count=30,
        notes="rf test",
    )

    assert record.model_type == "random_forest"

    loaded = registry.load_model("rf-model", "0.1.0")
    assert loaded.is_trained
    assert loaded.model_type == "random_forest"
    np.testing.assert_array_equal(loaded.predict(np.zeros((1, 12))), model.predict(np.zeros((1, 12))))


def test_sqlite_registry_stores_and_loads_deep_model(tmp_path):
    registry = SQLiteModelRegistry(tmp_path)
    model = _trained_deep_model()
    record = registry.register(
        model,
        name="deep-model",
        version="0.1.0",
        training_metrics={"train_accuracy": 0.85},
        training_sample_count=30,
        notes="deep test",
    )

    assert record.model_type == "deep_neural_network"

    loaded = registry.load_model("deep-model", "0.1.0")
    assert loaded.is_trained
    assert loaded.model_type == "deep_neural_network"
    np.testing.assert_array_equal(loaded.predict(np.zeros((1, 12))), model.predict(np.zeros((1, 12))))


def test_sqlite_registry_get_record_includes_model_type(tmp_path):
    registry = SQLiteModelRegistry(tmp_path)
    model = _trained_rf_model()
    registry.register(
        model,
        name="rf-model",
        version="0.2.0",
        training_metrics={"train_accuracy": 0.9},
        training_sample_count=30,
        notes="rf test 2",
    )

    record = registry.get_record("rf-model", "0.2.0")
    assert record.model_type == "random_forest"
