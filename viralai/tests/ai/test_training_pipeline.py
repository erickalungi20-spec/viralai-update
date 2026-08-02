import pytest

from viralai.ai.features import FeatureContext
from viralai.ai.registry import ModelRegistry
from viralai.ai.training_pipeline import AITrainingPipelineManager, LabeledExample
from viralai.common.errors import ValidationError
from viralai.core.idm import Mutation, MutationType


def _labeled_examples(n: int = 40, hotspot_threshold: float = 0.5) -> list[LabeledExample]:
    examples = []
    for i in range(n):
        position = i * 10
        genome_length = n * 10
        mutation = Mutation(
            position=position,
            reference_base="A",
            observed_base="G",
            mutation_type=MutationType.SUBSTITUTION,
            confidence_score=0.9,
        )
        context = FeatureContext(genome_length=genome_length, entropy_at_position=(i % n) / n)
        label = int((position / genome_length) > hotspot_threshold)
        examples.append(LabeledExample(mutation=mutation, context=context, label=label))
    return examples


def test_pipeline_runs_end_to_end_and_registers_model(tmp_path):
    registry = ModelRegistry(tmp_path)
    pipeline = AITrainingPipelineManager(registry)

    report = pipeline.run(
        name="hotspot-model",
        version="0.1.0",
        training_examples=_labeled_examples(),
        notes="Phase 4 test run",
    )

    assert "train_accuracy" in report.training_metrics
    assert report.validation_metrics is None
    assert len(report.feature_importances) == 12
    assert report.model_record.name == "hotspot-model"

    # model should actually be loadable from the registry afterward
    loaded = registry.load_model("hotspot-model", "0.1.0")
    assert loaded.is_trained


def test_pipeline_with_validation_set_populates_validation_metrics(tmp_path):
    registry = ModelRegistry(tmp_path)
    pipeline = AITrainingPipelineManager(registry)

    examples = _labeled_examples(n=60)
    training_examples, validation_examples = examples[:40], examples[40:]

    report = pipeline.run(
        name="hotspot-model",
        version="0.1.0",
        training_examples=training_examples,
        validation_examples=validation_examples,
    )

    assert report.validation_metrics is not None
    assert "accuracy" in report.validation_metrics
    assert any(key.startswith("val_") for key in report.training_metrics)
    record = registry.get_record("hotspot-model", "0.1.0")
    assert any(key.startswith("val_") for key in record.training_metrics)


def test_pipeline_selects_best_model_by_validation(tmp_path):
    registry = ModelRegistry(tmp_path)
    pipeline = AITrainingPipelineManager(registry)

    examples = _labeled_examples(n=100)
    training_examples, validation_examples = examples[:80], examples[80:]

    report = pipeline.run(
        name="selected-model",
        version="0.2.0",
        training_examples=training_examples,
        validation_examples=validation_examples,
    )

    assert report.model_record.name == "selected-model"
    assert report.model_record.version == "0.2.0"
    assert report.model_record.model_type in {"random_forest", "deep_neural_network"}
    assert report.validation_metrics is not None
    assert any(key.startswith("val_") for key in report.training_metrics)


def test_pipeline_rejects_empty_training_set(tmp_path):
    registry = ModelRegistry(tmp_path)
    pipeline = AITrainingPipelineManager(registry)

    with pytest.raises(ValidationError):
        pipeline.run(name="hotspot-model", version="0.1.0", training_examples=[])
