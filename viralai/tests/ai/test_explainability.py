import numpy as np
import pytest

from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FEATURE_NAMES
from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.common.errors import ValidationError


def _trained_model(n: int = 80, seed: int = 0) -> MutationHotspotModel:
    rng = np.random.RandomState(seed)
    X = rng.rand(n, len(FEATURE_NAMES))
    # label driven strongly by feature index 0 -- position_normalized in real usage
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    model.train(X, y)
    return model


def test_cannot_explain_untrained_model():
    model = MutationHotspotModel()
    with pytest.raises(ValidationError):
        ShapExplainer(model)


def test_explain_instance_returns_all_feature_names():
    model = _trained_model()
    explainer = ShapExplainer(model)

    explanation = explainer.explain_instance(np.random.RandomState(1).rand(len(FEATURE_NAMES)))

    assert set(explanation.keys()) == set(FEATURE_NAMES)
    assert all(isinstance(v, float) for v in explanation.values())


def test_explain_batch_returns_one_explanation_per_row():
    model = _trained_model()
    explainer = ShapExplainer(model)
    X = np.random.RandomState(2).rand(5, len(FEATURE_NAMES))

    explanations = explainer.explain_batch(X)

    assert len(explanations) == 5


def test_dominant_feature_is_identifiable_via_top_features():
    """The synthetic dataset's label is driven almost entirely by feature 0
    (position_normalized). SHAP should reflect that this feature dominates the
    explanation for an instance that's strongly on one side of the decision boundary.
    """
    model = _trained_model(n=200)
    explainer = ShapExplainer(model)

    # an instance strongly positioned to trigger the positive class on feature 0
    x_row = np.full(len(FEATURE_NAMES), 0.5)
    x_row[0] = 0.99

    top = explainer.top_features(x_row, n=1)

    assert top[0][0] == "position_normalized"


def test_top_features_respects_n():
    model = _trained_model()
    explainer = ShapExplainer(model)
    x_row = np.random.RandomState(3).rand(len(FEATURE_NAMES))

    top = explainer.top_features(x_row, n=3)

    assert len(top) == 3
    # sorted by absolute magnitude, descending
    magnitudes = [abs(v) for _, v in top]
    assert magnitudes == sorted(magnitudes, reverse=True)


class TestExtractPositiveClassValues:
    """Directly exercises the defensive shape-validation logic that protects against a
    future shap/sklearn version silently changing its output convention (see the
    module docstring and ADR-007).
    """

    def test_wrong_list_length_raises(self):
        from viralai.ai.explainability import _extract_positive_class_values

        with pytest.raises(ValidationError):
            _extract_positive_class_values([np.zeros((1, len(FEATURE_NAMES)))], expected_rows=1)

    def test_wrong_ndarray_shape_raises(self):
        from viralai.ai.explainability import _extract_positive_class_values

        bad_shape = np.zeros((1, len(FEATURE_NAMES)))  # missing the class dimension
        with pytest.raises(ValidationError):
            _extract_positive_class_values(bad_shape, expected_rows=1)

    def test_correct_3d_shape_extracts_class_1(self):
        from viralai.ai.explainability import _extract_positive_class_values

        raw = np.zeros((2, len(FEATURE_NAMES), 2))
        raw[:, :, 1] = 5.0  # class-1 values distinguishable from class-0 (left at 0.0)

        result = _extract_positive_class_values(raw, expected_rows=2)

        assert result.shape == (2, len(FEATURE_NAMES))
        assert np.all(result == 5.0)

    def test_legacy_list_of_two_arrays_extracts_second_element(self):
        from viralai.ai.explainability import _extract_positive_class_values

        class_0 = np.zeros((2, len(FEATURE_NAMES)))
        class_1 = np.full((2, len(FEATURE_NAMES)), 7.0)

        result = _extract_positive_class_values([class_0, class_1], expected_rows=2)

        assert np.all(result == 7.0)

    def test_row_count_mismatch_raises(self):
        from viralai.ai.explainability import _extract_positive_class_values

        raw = np.zeros((3, len(FEATURE_NAMES), 2))
        with pytest.raises(ValidationError):
            _extract_positive_class_values(raw, expected_rows=99)
