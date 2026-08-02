"""
Phase 4 AI Engine: feature engineering, the Mutation Hotspot Model (Random Forest
baseline), real per-prediction SHAP explanations, a versioned Model Registry, the AI
Training Pipeline Manager that enforces one consistent training process, and the
Scientific Reasoning Engine that ties predictions back to the Research Graph.
"""

from viralai.ai.dataset_repository import DatasetRepository
from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FEATURE_NAMES, FeatureContext, extract_features, to_vector
from viralai.ai.hotspot_model import DeepMutationModel, MutationHotspotModel
from viralai.ai.reasoning import ReasoningRecord, ScientificReasoningEngine
from viralai.ai.registry import ModelRecord, ModelRegistry
from viralai.ai.training_pipeline import AITrainingPipelineManager, LabeledExample, PipelineReport

__all__ = [
    "FEATURE_NAMES",
    "FeatureContext",
    "extract_features",
    "to_vector",
    "MutationHotspotModel",
    "DeepMutationModel",
    "ShapExplainer",
    "ModelRegistry",
    "ModelRecord",
    "DatasetRepository",
    "AITrainingPipelineManager",
    "LabeledExample",
    "PipelineReport",
    "ScientificReasoningEngine",
    "ReasoningRecord",
]
