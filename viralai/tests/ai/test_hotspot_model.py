import numpy as np
import pytest

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.common.errors import ValidationError


def _synthetic_dataset(n: int = 60, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """A deterministic dataset where the label is a clean function of feature 0 and 1
    (mirrors 'position_normalized' and 'confidence_score' in real usage), so a Random
    Forest can learn it reliably and tests aren't flaky.
    """
    rng = np.random.RandomState(seed)
    X = rng.rand(n, 12)  # matches len(FEATURE_NAMES)
    y = ((X[:, 0] > 0.5) & (X[:, 4] > 0.5)).astype(int)
    return X, y


def test_predict_before_train_raises():
    model = MutationHotspotModel()
    with pytest.raises(ValidationError):
        model.predict(np.zeros((1, 12)))


def test_train_returns_metrics_and_marks_trained():
    model = MutationHotspotModel()
    X, y = _synthetic_dataset()

    metrics = model.train(X, y)

    assert model.is_trained
    assert 0.0 <= metrics["train_accuracy"] <= 1.0
    assert "train_f1" in metrics


def test_train_rejects_mismatched_lengths():
    model = MutationHotspotModel()
    with pytest.raises(ValidationError):
        model.train(np.zeros((5, 12)), np.zeros(3))


def test_train_rejects_empty_dataset():
    model = MutationHotspotModel()
    with pytest.raises(ValidationError):
        model.train(np.zeros((0, 12)), np.zeros(0))


def test_predict_proba_returns_values_between_zero_and_one():
    model = MutationHotspotModel()
    X, y = _synthetic_dataset()
    model.train(X, y)

    probabilities = model.predict_proba(X)

    assert probabilities.shape == (len(X),)
    assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))


def test_feature_importances_before_train_raises():
    model = MutationHotspotModel()
    with pytest.raises(ValidationError):
        model.feature_importances()


def test_feature_importances_sum_to_approximately_one():
    model = MutationHotspotModel()
    X, y = _synthetic_dataset()
    model.train(X, y)

    importances = model.feature_importances()

    assert len(importances) == 12
    assert sum(importances.values()) == pytest.approx(1.0, abs=1e-6)


def test_model_learns_the_synthetic_signal_reasonably_well():
    """Not a strict accuracy threshold test (avoid flakiness) -- just confirms the model
    does meaningfully better than a coin flip on a dataset with a real signal.
    """
    model = MutationHotspotModel()
    X, y = _synthetic_dataset(n=200)
    metrics = model.train(X, y)

    assert metrics["train_accuracy"] > 0.7


def test_deep_model_learns_the_synthetic_signal():
    from viralai.ai.hotspot_model import DeepMutationModel

    model = DeepMutationModel(max_iter=400)
    X, y = _synthetic_dataset(n=200)
    metrics = model.train(X, y)

    assert model.is_trained
    assert metrics["train_accuracy"] > 0.7
    assert 0.0 <= metrics["train_f1"] <= 1.0
