import pytest

from viralai.common.errors import WorkflowError
from viralai.core.engine import CoreEngine
from viralai.core.idm import AnalysisStatus
from viralai.workflow.checkpoint import CheckpointManager
from viralai.workflow.runner import WorkflowRunner


def test_successful_workflow_completes_and_clears_checkpoint(tmp_path):
    engine = CoreEngine()
    checkpoints = CheckpointManager(tmp_path)
    runner = WorkflowRunner(engine, checkpoints)

    calls = []

    def step_one(ctx):
        calls.append("one")
        ctx.analysis.results["a"] = 1

    def step_two(ctx):
        calls.append("two")
        ctx.analysis.results["b"] = 2

    analysis = runner.run("test-workflow", [step_one, step_two], run_id="run-1")

    assert analysis.status == AnalysisStatus.COMPLETED
    assert calls == ["one", "two"]
    assert analysis.results == {"a": 1, "b": 2}
    assert checkpoints.exists("run-1") is False  # cleared on success


def test_failing_step_preserves_checkpoint_and_raises(tmp_path):
    engine = CoreEngine()
    checkpoints = CheckpointManager(tmp_path)
    runner = WorkflowRunner(engine, checkpoints)

    def step_one(ctx):
        ctx.analysis.results["a"] = 1

    def failing_step(ctx):
        raise ValueError("boom")

    with pytest.raises(WorkflowError):
        runner.run("test-workflow", [step_one, failing_step], run_id="run-2")

    assert checkpoints.exists("run-2") is True
    checkpoint = checkpoints.load("run-2")
    assert checkpoint.completed_step_index == 0  # step_one succeeded before failure
    assert checkpoint.results == {"a": 1}


def test_resume_skips_already_completed_steps(tmp_path):
    engine = CoreEngine()
    checkpoints = CheckpointManager(tmp_path)
    runner = WorkflowRunner(engine, checkpoints)

    call_counts = {"one": 0, "two": 0}

    def step_one(ctx):
        call_counts["one"] += 1
        ctx.analysis.results["a"] = 1

    def failing_then_recorded_step(ctx):
        call_counts["two"] += 1
        if call_counts["two"] == 1:
            raise ValueError("first attempt fails")
        ctx.analysis.results["b"] = 2

    # first attempt: step_one succeeds, step_two fails
    with pytest.raises(WorkflowError):
        runner.run("resumable-workflow", [step_one, failing_then_recorded_step], run_id="run-3")

    assert call_counts == {"one": 1, "two": 1}

    # second attempt (resume): step_one should NOT run again
    analysis = runner.run(
        "resumable-workflow", [step_one, failing_then_recorded_step], run_id="run-3"
    )

    assert call_counts == {"one": 1, "two": 2}  # step_one still only called once total
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.results == {"a": 1, "b": 2}


def test_retry_recovers_from_transient_failure(tmp_path):
    engine = CoreEngine()
    checkpoints = CheckpointManager(tmp_path)
    runner = WorkflowRunner(engine, checkpoints, max_retries=2)

    attempts = {"count": 0}

    def flaky_step(ctx):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("transient failure")
        ctx.analysis.results["done"] = True

    analysis = runner.run("flaky-workflow", [flaky_step], run_id="run-4")

    assert attempts["count"] == 3
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.results == {"done": True}


def test_retry_exhausted_still_raises(tmp_path):
    engine = CoreEngine()
    checkpoints = CheckpointManager(tmp_path)
    runner = WorkflowRunner(engine, checkpoints, max_retries=1)

    attempts = {"count": 0}

    def always_fails(ctx):
        attempts["count"] += 1
        raise ValueError("always fails")

    with pytest.raises(WorkflowError):
        runner.run("always-failing-workflow", [always_fails], run_id="run-5")

    assert attempts["count"] == 2  # initial attempt + 1 retry


def test_default_run_id_is_generated_when_not_provided(tmp_path):
    engine = CoreEngine()
    checkpoints = CheckpointManager(tmp_path)
    runner = WorkflowRunner(engine, checkpoints)

    def step(ctx):
        ctx.analysis.results["x"] = 1

    analysis = runner.run("auto-id-workflow", [step])

    assert analysis.analysis_id  # some id was generated
