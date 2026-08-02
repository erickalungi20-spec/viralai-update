import numpy as np

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.core.engine import CoreEngine
from viralai.core.idm import AnalysisStatus
from viralai.workflow.checkpoint import CheckpointManager
from viralai.workflow.runner import WorkflowRunner
from viralai.workflow.templates import make_ai_hotspot_step


def test_make_ai_hotspot_step_runs_predictions_and_stores_json_safe_results(tmp_path):
    rng = np.random.RandomState(0)
    X_train = rng.rand(50, 3)
    y_train = (X_train[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    model.train(X_train, y_train)

    feature_vectors = [[0.9, 0.1, 0.1], [0.1, 0.9, 0.1]]
    step = make_ai_hotspot_step(model, feature_vectors)

    engine = CoreEngine()
    runner = WorkflowRunner(engine, CheckpointManager(tmp_path))
    analysis = runner.run("ai-hotspot-test", [step])

    assert analysis.status == AnalysisStatus.COMPLETED
    ai_results = analysis.results["ai_predictions"]
    assert len(ai_results["predictions"]) == 2
    assert len(ai_results["confidences"]) == 2
    assert all(0.0 <= c <= 1.0 for c in ai_results["confidences"])
