"""
Explainable AI Module (Blueprint Ch.26.7).

Real per-prediction explanations via SHAP's TreeExplainer, not a hand-waved
"feature_importances_ is close enough" substitute. Global feature importance
(hotspot_model.feature_importances()) answers "what matters across all predictions";
this module answers "why did this specific prediction come out this way", which is what
Ch.26.7 actually requires ("every AI prediction shall include... feature importance").

Implementation note pinned to the installed shap version's behavior: for a binary
RandomForestClassifier, `TreeExplainer.shap_values(X)` may return either a 2D array
of shape (n_samples, n_features) when the positive-class contribution is already
exposed directly or a 3D array of shape (n_samples, n_features, 2) for the two-class
output. This module always reads class index 1 (the "hotspot=True" class) for the
3D convention; if a future shap/sklearn version changes that shape, the validation in
`_extract_positive_class_values` fails loudly rather than silently returning
explanations for the wrong class.
"""

from __future__ import annotations

import numpy as np
import shap

from viralai.ai.features import FEATURE_NAMES
from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger

logger = get_logger("ai.explainability")


class ShapExplainer:
    """Wraps a trained MutationHotspotModel with SHAP TreeExplainer for per-prediction
    feature attribution.
    """

    def __init__(self, model: MutationHotspotModel) -> None:
        if not model.is_trained:
            raise ValidationError("Cannot build an explainer for an untrained model")
        self._model = model
        self._explainer = shap.TreeExplainer(model.sklearn_model)

    def explain_instance(self, x_row: np.ndarray) -> dict[str, float]:
        """Return {feature_name: shap_value} for one instance (1D array of length
        len(FEATURE_NAMES)). Positive values pushed the prediction toward "hotspot";
        negative values pushed it away.
        """
        return self.explain_batch(x_row.reshape(1, -1))[0]

    def explain_batch(self, X: np.ndarray) -> list[dict[str, float]]:
        raw_shap_values = self._explainer.shap_values(X)
        positive_class_values = _extract_positive_class_values(
            raw_shap_values, expected_rows=len(X)
        )

        explanations: list[dict[str, float]] = []
        for row in positive_class_values:
            explanations.append(dict(zip(FEATURE_NAMES, row)))
        return explanations

    def top_features(self, x_row: np.ndarray, n: int = 3) -> list[tuple[str, float]]:
        """The `n` features with the largest absolute contribution to one prediction —
        this is what a report-facing "why did the model flag this mutation" summary
        should actually display, rather than all 12 features indiscriminately.
        """
        explanation = self.explain_instance(x_row)
        ranked = sorted(explanation.items(), key=lambda item: abs(item[1]), reverse=True)
        return ranked[:n]


def _extract_positive_class_values(
    raw_shap_values: np.ndarray, *, expected_rows: int
) -> np.ndarray:
    """Normalize SHAP output for a binary classifier into a
    (n_samples, n_features) array of class-1 (positive/"hotspot") contributions.

    Different SHAP/sklearn versions return slightly different shapes for the same model:
    - a 2D array of shape (n_samples, n_features) when the positive-class contribution is
      already exposed directly,
    - a 3D array of shape (n_samples, n_features, 2) for the two-class output, or
    - a list of per-class arrays (older versions).

    The function accepts these conventions explicitly instead of assuming a single shape
    and silently attributing explanations to the wrong class.
    """
    if isinstance(raw_shap_values, list):
        # Only a two-element list (per-class arrays) is accepted for legacy SHAP outputs.
        if len(raw_shap_values) == 2:
            positive = np.asarray(raw_shap_values[1])
        else:
            raise ValidationError(
                f"Expected a 2-element list of SHAP arrays for binary classification, got {len(raw_shap_values)}"
            )
    else:
        array = np.asarray(raw_shap_values)
        if array.ndim == 2:
            # Newer SHAP versions may already expose the positive-class contribution as a
            # 2D matrix; accept it as-is when it matches the expected sample/feature shape.
            positive = array
        elif array.ndim == 3:
            if array.shape[2] == 1:
                positive = array[:, :, 0]
            elif array.shape[2] == 2:
                positive = array[:, :, 1]
            else:
                raise ValidationError(
                    f"Unexpected SHAP output shape {array.shape} — expected a 2D array "
                    f"or a 3D array with 2 classes for binary classification."
                )
        else:
            raise ValidationError(
                f"Unexpected SHAP output shape {array.shape} — expected a 2D array "
                f"or a 3D array with 2 classes for binary classification."
            )

    if positive.ndim != 2:
        raise ValidationError(
            f"SHAP output shape {positive.shape} is not a 2D contribution matrix"
        )

    if positive.shape[0] != expected_rows or positive.shape[1] != len(FEATURE_NAMES):
        raise ValidationError(
            f"SHAP output shape {positive.shape} does not match expected "
            f"({expected_rows}, {len(FEATURE_NAMES)})"
        )
    return positive
