"""
Core Engine.

The orchestration hub (Blueprint Ch.15). It owns no biological knowledge — it wires
together the Event Bus, Task Scheduler, Plugin Manager, and Provenance Manager, and drives
the workflow lifecycle: initialize -> validate -> load plugin -> execute -> record ->
export. Real analytical steps (Mutation Engine etc.) are Phase 2+; this phase proves the
skeleton works.
"""

from __future__ import annotations

from typing import Any, Callable

from viralai.common.errors import WorkflowError
from viralai.common.ids import new_id
from viralai.common.logging import get_logger
from viralai.core.event_bus import EventBus
from viralai.core.idm import Analysis, AnalysisStatus
from viralai.core.plugin_manager import PluginManager
from viralai.core.provenance import ProvenanceManager
from viralai.core.scheduler import TaskScheduler

logger = get_logger("core.engine")

WorkflowStep = Callable[["WorkflowContext"], None]


class WorkflowContext:
    """State passed through a workflow's steps: the running Analysis plus shared services."""

    def __init__(self, analysis: Analysis, engine: "CoreEngine") -> None:
        self.analysis = analysis
        self.engine = engine

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.engine.event_bus.publish(topic, payload, source=self.analysis.workflow_name)

    def record_step(self, step_name: str, **details: Any) -> None:
        self.engine.provenance.get(self.analysis.analysis_id).record_step(step_name, **details)


class CoreEngine:
    """Wires up Phase 0's shared services and runs workflows against them.

    One CoreEngine per application/test — not a global singleton, so tests can run in
    isolation and a future multi-tenant deployment isn't fighting shared module state.
    """

    def __init__(self, max_scheduler_workers: int = 4) -> None:
        self.event_bus = EventBus()
        self.scheduler = TaskScheduler(max_workers=max_scheduler_workers)
        self.plugins = PluginManager()
        self.provenance = ProvenanceManager()
        self._analyses: dict[str, Analysis] = {}

    def run_workflow(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        configuration: dict[str, Any] | None = None,
    ) -> Analysis:
        """Execute `steps` in order against a fresh Analysis + ProvenanceRecord.

        This is intentionally synchronous and linear for Phase 0 — the Workflow Engine's
        richer scheduling/templating (Ch.17) is Phase 7 scope. This proves the lifecycle:
        initialize -> validate -> execute -> record -> (fail loudly or) complete.
        """
        analysis = Analysis(
            analysis_id=new_id("analysis"),
            workflow_name=workflow_name,
            status=AnalysisStatus.RUNNING,
            configuration=configuration or {},
        )
        self._analyses[analysis.analysis_id] = analysis
        self.provenance.start(analysis.analysis_id, parameters=analysis.configuration)
        logger.info("workflow started: %s (analysis_id=%s)", workflow_name, analysis.analysis_id)

        context = WorkflowContext(analysis=analysis, engine=self)
        try:
            for step in steps:
                step_name = getattr(step, "__name__", repr(step))
                context.record_step(f"before:{step_name}")
                step(context)
                context.record_step(f"after:{step_name}")
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed WorkflowError
            analysis.status = AnalysisStatus.FAILED
            analysis.error = f"{type(exc).__name__}: {exc}"
            self.provenance.finalize(analysis.analysis_id)
            logger.exception(
                "workflow failed: %s (analysis_id=%s)", workflow_name, analysis.analysis_id
            )
            raise WorkflowError(
                f"Workflow '{workflow_name}' failed at analysis {analysis.analysis_id}: {exc}"
            ) from exc

        analysis.status = AnalysisStatus.COMPLETED
        self.provenance.finalize(analysis.analysis_id)
        logger.info("workflow completed: %s (analysis_id=%s)", workflow_name, analysis.analysis_id)
        return analysis

    def get_analysis(self, analysis_id: str) -> Analysis:
        return self._analyses[analysis_id]
