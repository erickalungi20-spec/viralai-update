"""
Mutation Hotspot Model (Blueprint Ch.26.5).

A thin, explicit wrapper around scikit-learn's RandomForestClassifier — Phase 4 starts
with the interpretable classical ML baseline the blueprint specifies first, not deep
learning. Deep learning scaffolding (Ch.26.6) is a documented later addition once there's
a real dataset large enough to justify it; this module also includes a feed-forward
neural network wrapper so the platform can compare a classical baseline against a
higher-capacity model and choose the best performer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.neural_network import MLPClassifier

from viralai.ai.features import FEATURE_NAMES
from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger

logger = get_logger("ai.hotspot_model")


class MutationModelBase(ABC):
    model_type: str

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        ...

    @abstractmethod
    def feature_importances(self) -> dict[str, float]:
        ...

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        ...

    @property
    @abstractmethod
    def sklearn_model(self):
        ...


class MutationHotspotModel(MutationModelBase):
    """Predicts whether a mutation is a 'hotspot' (however the caller has labeled that —
    this model has no opinion on the label's biological definition, it just learns the
    mapping from features to whatever binary label it's trained on).
    """

    model_type = "random_forest"

    def __init__(self, n_estimators: int = 100, random_state: int = 42) -> None:
        self._model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
        self._is_trained = False

    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Fit the model and return training-set metrics. Training-set metrics are not a
        substitute for held-out validation (Phase 10's Benchmark Repository does that
        properly) — they exist here for a quick sanity check, not as a claim of
        generalization performance.
        """
        if len(X) != len(y):
            raise ValidationError(f"X has {len(X)} rows but y has {len(y)} labels")
        if len(X) == 0:
            raise ValidationError("Cannot train on an empty dataset")

        self._model.fit(X, y)
        self._is_trained = True

        predictions = self._model.predict(X)
        metrics = {
            "train_accuracy": accuracy_score(y, predictions),
            "train_precision": precision_score(y, predictions, zero_division=0),
            "train_recall": recall_score(y, predictions, zero_division=0),
            "train_f1": f1_score(y, predictions, zero_division=0),
        }
        logger.info("model trained on %d samples: %s", len(X), metrics)
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        self._require_trained()
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(hotspot=1) per row — this is the 'confidence score' the blueprint
        requires every AI prediction to carry (Ch.26.7).
        """
        self._require_trained()
        return self._model.predict_proba(X)[:, 1]

    def feature_importances(self) -> dict[str, float]:
        """Global (not per-prediction) feature importance from the trained forest. For
        per-prediction explanations, use `viralai.ai.explainability.ShapExplainer`
        instead — global importance answers 'what matters overall', SHAP answers 'why
        did THIS prediction come out this way'.
        """
        self._require_trained()
        return dict(zip(FEATURE_NAMES, self._model.feature_importances_))

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def sklearn_model(self) -> RandomForestClassifier:
        """Escape hatch for the explainability module, which needs the raw sklearn
        estimator to construct a SHAP TreeExplainer.
        """
        return self._model

    def _require_trained(self) -> None:
        if not self._is_trained:
            raise ValidationError("Model has not been trained yet — call train() first")


class DeepMutationModel(MutationModelBase):
    """A simple deep-learning variant built on a feed-forward neural network.

    This model is intentionally shallow enough to remain practical in Phase 4,
    while still allowing the platform to compare classical and deep learners and
    select the best performing option automatically.
    """

    model_type = "deep_neural_network"

    def __init__(
        self,
        hidden_layer_sizes: tuple[int, ...] = (32, 16),
        random_state: int = 42,
        max_iter: int = 300,
    ) -> None:
        self._model = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            activation="relu",
            solver="adam",
            max_iter=max_iter,
            random_state=random_state,
        )
        self._is_trained = False

    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        if len(X) != len(y):
            raise ValidationError(f"X has {len(X)} rows but y has {len(y)} labels")
        if len(X) == 0:
            raise ValidationError("Cannot train on an empty dataset")

        self._model.fit(X, y)
        self._is_trained = True

        predictions = self._model.predict(X)
        metrics = {
            "train_accuracy": accuracy_score(y, predictions),
            "train_precision": precision_score(y, predictions, zero_division=0),
            "train_recall": recall_score(y, predictions, zero_division=0),
            "train_f1": f1_score(y, predictions, zero_division=0),
        }
        logger.info("deep model trained on %d samples: %s", len(X), metrics)
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        self._require_trained()
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._require_trained()
        return self._model.predict_proba(X)[:, 1]

    def feature_importances(self) -> dict[str, float]:
        self._require_trained()
        # Use the absolute contributions of the first layer weights as a rough feature
        # importance proxy for neural nets. This is not as interpretable as tree-based
        # importances, but it gives a consistent global signal for model comparison.
        first_layer = np.asarray(self._model.coefs_[0])
        importance_scores = np.sum(np.abs(first_layer), axis=1)
        if importance_scores.sum() == 0:
            importance_scores = np.ones_like(importance_scores)
        normalized = importance_scores / float(np.sum(importance_scores))
        return dict(zip(FEATURE_NAMES, normalized.tolist()))

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def sklearn_model(self) -> MLPClassifier:
        return self._model

    def _require_trained(self) -> None:
        if not self._is_trained:
            raise ValidationError("Model has not been trained yet — call train() first")
