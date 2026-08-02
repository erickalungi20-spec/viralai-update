import pytest

from viralai.common.errors import WorkflowError
from viralai.core.engine import CoreEngine
from viralai.core.idm import AnalysisStatus
from viralai.core.plugin_manager import PluginManager


class HelloWorldPlugin:
    """The smallest possible object satisfying the ViralAIPlugin protocol."""

    name = "hello-world"
    version = "0.1.0"
    supported_virus = "TestVirus"


def test_hello_world_plugin_can_be_registered_and_retrieved():
    manager = PluginManager()
    manager.register(HelloWorldPlugin())

    plugin = manager.get("hello-world")

    assert plugin.supported_virus == "TestVirus"
    assert manager.list_plugins() == ["hello-world"]


def test_run_workflow_completes_and_records_provenance():
    engine = CoreEngine()

    def step_one(ctx):
        ctx.record_step("did-step-one")
        ctx.publish("test.step_one_done", {"ok": True})

    def step_two(ctx):
        ctx.record_step("did-step-two")

    analysis = engine.run_workflow("hello-world-workflow", [step_one, step_two])

    assert analysis.status == AnalysisStatus.COMPLETED
    provenance = engine.provenance.get(analysis.analysis_id)
    assert provenance.finished_at is not None
    step_names = [s["step"] for s in provenance.steps]
    assert "did-step-one" in step_names
    assert "did-step-two" in step_names

    events = engine.event_bus.history("test.step_one_done")
    assert len(events) == 1
    assert events[0].payload == {"ok": True}


def test_run_workflow_failure_is_recorded_and_raised():
    engine = CoreEngine()

    def failing_step(ctx):
        raise ValueError("something biological went wrong")

    with pytest.raises(WorkflowError):
        engine.run_workflow("broken-workflow", [failing_step])

    # the analysis should still be retrievable, marked failed, with provenance closed out
    [analysis_id] = list(engine._analyses.keys())
    analysis = engine.get_analysis(analysis_id)
    assert analysis.status == AnalysisStatus.FAILED
    assert "something biological went wrong" in analysis.error

    provenance = engine.provenance.get(analysis_id)
    assert provenance.finished_at is not None


def test_scheduler_and_plugin_manager_are_available_on_the_engine():
    engine = CoreEngine()
    engine.plugins.register(HelloWorldPlugin())

    job = engine.scheduler.submit(lambda: 21 * 2, name="answer")
    assert engine.scheduler.result(job.job_id, timeout=5) == 42
    assert engine.plugins.get("hello-world").name == "hello-world"

    engine.scheduler.shutdown()
