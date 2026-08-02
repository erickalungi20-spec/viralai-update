import pytest

from viralai.common.errors import ValidationError
from viralai.workflow.checkpoint import Checkpoint, CheckpointManager


def test_save_and_load_round_trip(tmp_path):
    manager = CheckpointManager(tmp_path)
    checkpoint = Checkpoint(
        workflow_run_id="run-1",
        completed_step_index=2,
        results={"mutations": [1, 2, 3]},
        configuration={"x": 1},
    )

    manager.save(checkpoint)
    loaded = manager.load("run-1")

    assert loaded is not None
    assert loaded.completed_step_index == 2
    assert loaded.results == {"mutations": [1, 2, 3]}
    assert loaded.configuration == {"x": 1}


def test_load_nonexistent_returns_none(tmp_path):
    manager = CheckpointManager(tmp_path)
    assert manager.load("nonexistent") is None


def test_exists(tmp_path):
    manager = CheckpointManager(tmp_path)
    assert manager.exists("run-1") is False
    manager.save(
        Checkpoint(workflow_run_id="run-1", completed_step_index=0, results={}, configuration={})
    )
    assert manager.exists("run-1") is True


def test_clear_removes_checkpoint(tmp_path):
    manager = CheckpointManager(tmp_path)
    manager.save(
        Checkpoint(workflow_run_id="run-1", completed_step_index=0, results={}, configuration={})
    )

    manager.clear("run-1")

    assert manager.exists("run-1") is False


def test_clear_nonexistent_does_not_raise(tmp_path):
    manager = CheckpointManager(tmp_path)
    manager.clear("nonexistent")  # should not raise


def test_save_rejects_non_json_serializable_results(tmp_path):
    manager = CheckpointManager(tmp_path)
    checkpoint = Checkpoint(
        workflow_run_id="run-1", completed_step_index=0, results={"bad": object()}, configuration={}
    )
    with pytest.raises(ValidationError):
        manager.save(checkpoint)


def test_invalid_run_id_rejected(tmp_path):
    manager = CheckpointManager(tmp_path)
    with pytest.raises(ValidationError):
        manager.save(
            Checkpoint(
                workflow_run_id="../escape", completed_step_index=0, results={}, configuration={}
            )
        )


def test_saving_again_overwrites_previous_checkpoint(tmp_path):
    manager = CheckpointManager(tmp_path)
    manager.save(
        Checkpoint(
            workflow_run_id="run-1", completed_step_index=0, results={"a": 1}, configuration={}
        )
    )
    manager.save(
        Checkpoint(
            workflow_run_id="run-1", completed_step_index=1, results={"a": 2}, configuration={}
        )
    )

    loaded = manager.load("run-1")

    assert loaded.completed_step_index == 1
    assert loaded.results == {"a": 2}
