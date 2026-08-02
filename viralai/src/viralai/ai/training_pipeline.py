"""
AI Training Pipeline Manager.

From the engineering review (Recommendation 7): every model goes through the same
enforced sequence -- Dataset -> Feature Engineering -> Training -> Validation ->
Explainability -> Registration -- rather than each model being trained ad hoc with its
own one-off script. "Monitoring" and "Deployment" (the review's final two pipeline
stages) are Phase 11/12 concerns (they need a running service to monitor); this manager
covers the stages Phase 4 can actually deliver honestly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel

from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FeatureContext, extract_features, to_vector
from viralai.ai.hotspot_model import DeepMutationModel, MutationHotspotModel, MutationModelBase
from viralai.ai.registry import ModelRecord, ModelRegistry
from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger
from viralai.core.idm import Mutation

logger = get_logger("ai.training_pipeline")


@dataclass
class LabeledExample:
    mutation: Mutation
    context: FeatureContext
    label: int  # 1 = hotspot (or whatever binary concept the caller trains toward), 0 = not


class PipelineReport(BaseModel):
    training_metrics: dict[str, float]
    validation_metrics: dict[str, float] | None
    feature_importances: dict[str, float]
    model_record: ModelRecord


class AITrainingPipelineManager:
    """Runs the full Dataset -> Feature Engineering -> Training -> Validation ->
    Explainability -> Registration sequence and returns one report, rather than leaving
    each stage's output scattered across ad hoc script variables.
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def run(
        self,
        *,
        name: str,
        version: str,
        training_examples: list[LabeledExample],
        validation_examples: list[LabeledExample] | None = None,
        notes: str = "",
        ensemble: bool = False,
    ) -> PipelineReport:
        if not training_examples:
            raise ValidationError("Cannot run the training pipeline with zero training examples")

        # -- Feature Engineering --
        X_train, y_train = _vectorize(training_examples)
        logger.info("feature engineering complete: %d training rows", len(X_train))

        # -- Candidate Training --
        candidates: list[tuple[MutationModelBase, dict[str, float]]] = []

        rf_model = MutationHotspotModel()
        rf_metrics = rf_model.train(X_train, y_train)
        candidates.append((rf_model, rf_metrics))

        deep_model = DeepMutationModel()
        deep_metrics = deep_model.train(X_train, y_train)
        candidates.append((deep_model, deep_metrics))

        selected_model, selected_metrics = self._select_best_model(candidates, validation_examples, X_train, y_train)

        validation_metrics = self._evaluate_selected(selected_model, validation_examples)

        feature_importances = selected_model.feature_importances()

        if isinstance(selected_model, MutationHotspotModel):
            explainer = ShapExplainer(selected_model)
            explainer.explain_batch(X_train[: min(5, len(X_train))])
        else:
            logger.info("selected model is %s; per-row SHAP explanations are unavailable for this model type", selected_model.model_type)

        record = self._registry.register(
            selected_model,
            name=name,
            version=version,
            training_metrics={**selected_metrics, **_prefix(validation_metrics, "val_")},
            training_sample_count=len(training_examples),
            notes=notes,
        )

        return PipelineReport(
            training_metrics=selected_metrics,
            validation_metrics=validation_metrics,
            feature_importances=feature_importances,
            model_record=record,
        )

    def _select_best_model(
        self,
        candidates: list[tuple[MutationModelBase, dict[str, float]]],
        validation_examples: list[LabeledExample] | None,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> tuple[MutationModelBase, dict[str, float]]:
        if not validation_examples:
            logger.info("no validation examples provided, selecting based on training F1")
            return max(candidates, key=lambda item: item[1].get("train_f1", 0.0))

        X_val, y_val = _vectorize(validation_examples)
        scored_candidates: list[tuple[MutationModelBase, dict[str, float]]] = []
        for model, metrics in candidates:
            val_metrics = _evaluate(model, X_val, y_val)
            scored_metrics = {**metrics, **_prefix(val_metrics, "val_")}
            scored_candidates.append((model, scored_metrics))
            logger.info("model %s validation metrics: %s", model.model_type, val_metrics)

        return max(scored_candidates, key=lambda item: item[1].get("val_f1", item[1].get("train_f1", 0.0)))

    def _evaluate_selected(
        self,
        model: MutationModelBase,
        validation_examples: list[LabeledExample] | None,
    ) -> dict[str, float] | None:
        if not validation_examples:
            return None
        X_val, y_val = _vectorize(validation_examples)
        return _evaluate(model, X_val, y_val)


def _vectorize(examples: list[LabeledExample]) -> tuple[np.ndarray, np.ndarray]:
    feature_dicts = [extract_features(ex.mutation, ex.context) for ex in examples]
    X = to_vector(feature_dicts)
    y = np.array([ex.label for ex in examples])
    return X, y


def _evaluate(model: MutationHotspotModel, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    predictions = model.predict(X)
    return {
        "accuracy": accuracy_score(y, predictions),
        "precision": precision_score(y, predictions, zero_division=0),
        "recall": recall_score(y, predictions, zero_division=0),
        "f1": f1_score(y, predictions, zero_division=0),
    }


def _prefix(metrics: dict[str, float] | None, prefix: str) -> dict[str, float]:
    if not metrics:
        return {}
    return {f"{prefix}{k}": v for k, v in metrics.items()}
