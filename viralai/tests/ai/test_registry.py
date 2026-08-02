import numpy as np
import pytest

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.registry import ModelRegistry
from viralai.common.errors import ValidationError
import numpy as np
import pytest

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.registry import ModelRegistry
from viralai.common.errors import ValidationError


def _trained_model() -> MutationHotspotModel:
    rng = np.random.RandomState(0)
    X = rng.rand(30, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    model.train(X, y)
    return model


def test_cannot_register_untrained_model(tmp_path):
    registry = ModelRegistry(tmp_path)
    with pytest.raises(ValidationError):
        registry.register(
            MutationHotspotModel(),
            name="hotspot",
            version="0.1.0",
            training_metrics={},
            training_sample_count=0,
        )


def test_register_and_load_round_trip(tmp_path):
    registry = ModelRegistry(tmp_path)
    model = _trained_model()

    record = registry.register(
        model,
        name="hotspot",
        version="0.1.0",
        training_metrics={"train_accuracy": 0.9},
        training_sample_count=30,
        notes="test model",
    )

    assert record.name == "hotspot"
    assert record.version == "0.1.0"

    loaded = registry.load_model("hotspot", "0.1.0")
    assert loaded.is_trained
    # loaded model should produce identical predictions to the original
    X_test = np.random.RandomState(1).rand(5, 12)
    np.testing.assert_array_equal(loaded.predict(X_test), model.predict(X_test))


def test_duplicate_registration_raises(tmp_path):
    registry = ModelRegistry(tmp_path)
    model = _trained_model()
    registry.register(
        model, name="hotspot", version="0.1.0", training_metrics={}, training_sample_count=30
    )

    with pytest.raises(ValidationError):
        registry.register(
            model, name="hotspot", version="0.1.0", training_metrics={}, training_sample_count=30
        )


def test_get_record_for_unregistered_model_raises(tmp_path):
    registry = ModelRegistry(tmp_path)
    with pytest.raises(ValidationError):
        registry.get_record("nonexistent", "0.1.0")


def test_list_versions_and_latest_version(tmp_path):
    registry = ModelRegistry(tmp_path)
    model = _trained_model()

    registry.register(
        model, name="hotspot", version="0.1.0", training_metrics={}, training_sample_count=30
    )
    registry.register(
        model, name="hotspot", version="0.2.0", training_metrics={}, training_sample_count=30
    )

    versions = registry.list_versions("hotspot")
    assert set(versions) == {"0.1.0", "0.2.0"}
    assert registry.latest_version("hotspot") == "0.2.0"


def test_latest_version_for_unknown_model_is_none(tmp_path):
    registry = ModelRegistry(tmp_path)
    assert registry.latest_version("nonexistent") is None


def test_unsafe_identifiers_are_rejected(tmp_path):
    registry = ModelRegistry(tmp_path)
    model = _trained_model()
    with pytest.raises(ValidationError):
        registry.register(
            model, name="../escape", version="0.1.0", training_metrics={}, training_sample_count=1
        )


def test_list_model_names_returns_all_registered_model_names(tmp_path):
    registry = ModelRegistry(tmp_path)
    model = _trained_model()
    registry.register(
        model, name="model-a", version="0.1.0", training_metrics={}, training_sample_count=30
    )
    registry.register(
        model, name="model-b", version="0.1.0", training_metrics={}, training_sample_count=30
    )

    assert set(registry.list_model_names()) == {"model-a", "model-b"}


def test_list_model_names_empty_for_fresh_registry(tmp_path):
    registry = ModelRegistry(tmp_path)
    assert registry.list_model_names() == []
