"""
Workflow Runner (Blueprint Ch.17.6 Error Recovery, built on top of Phase 0's CoreEngine
workflow lifecycle rather than modifying it).

Adds two things CoreEngine.run_workflow doesn't have on its own: automatic checkpointing
after every successful step, and configurable per-step retry. Built as a separate class
composing a CoreEngine rather than changing engine.py, so Phase 0's tested lifecycle
stays untouched -- this is new capability layered on top, not a rewrite underneath it.

Known, documented scope limit: if a workflow is resumed after a failure, the resumed
run's ProvenanceRecord only captures the steps from the resume point onward, not merged
with the original failed attempt's partial history. Full cross-attempt provenance
stitching is a real feature, just not this one -- see ADR-010.
"""

from __future__ import annotations

from viralai.common.errors import WorkflowError
from viralai.common.ids import new_id
from viralai.common.logging import get_logger
from viralai.core.engine import CoreEngine, WorkflowContext, WorkflowStep
from viralai.core.idm import Analysis, AnalysisStatus
from viralai.workflow.checkpoint import Checkpoint, CheckpointManager

logger = get_logger("workflow.runner")


class WorkflowRunner:
    def __init__(
        self,
        core_engine: CoreEngine,
        checkpoint_manager: CheckpointManager,
        *,
        max_retries: int = 0,
    ) -> None:
        self._engine = core_engine
        self._checkpoints = checkpoint_manager
        self._max_retries = max_retries

    def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        configuration: dict | None = None,
        *,
        run_id: str | None = None,
    ) -> Analysis:
        run_id = run_id or new_id("run")
        configuration = configuration or {}

        checkpoint = self._checkpoints.load(run_id)
        start_index = checkpoint.completed_step_index + 1 if checkpoint else 0
        initial_results = checkpoint.results if checkpoint else {}
        if checkpoint:
            logger.info("resuming workflow run=%s from step %d", run_id, start_index)

        analysis = Analysis(
            analysis_id=run_id,
            workflow_name=workflow_name,
            status=AnalysisStatus.RUNNING,
            configuration=configuration,
        )
        analysis.results.update(initial_results)
        self._engine.provenance.start(run_id, parameters=configuration)
        context = WorkflowContext(analysis=analysis, engine=self._engine)

        for index, step in enumerate(steps):
            if index < start_index:
                continue  # already completed in a prior attempt, per the checkpoint

            self._run_step_with_retries(context, step, index, run_id)
            self._checkpoints.save(
                Checkpoint(
                    workflow_run_id=run_id,
                    completed_step_index=index,
                    results=analysis.results,
                    configuration=configuration,
                )
            )

        analysis.status = AnalysisStatus.COMPLETED
        self._engine.provenance.finalize(run_id)
        self._checkpoints.clear(run_id)
        logger.info("workflow completed: %s (run_id=%s)", workflow_name, run_id)
        return analysis

    def _run_step_with_retries(
        self, context: WorkflowContext, step: WorkflowStep, index: int, run_id: str
    ) -> None:
        step_name = getattr(step, "__name__", repr(step))
        attempts = 0
        while True:
            try:
                context.record_step(f"before:{step_name}")
                step(context)
                context.record_step(f"after:{step_name}")
                return
            except Exception as exc:  # noqa: BLE001 -- retried or re-raised as WorkflowError below
                attempts += 1
                if attempts <= self._max_retries:
                    logger.warning(
                        "step %d (%s) failed on attempt %d, retrying: %s",
                        index,
                        step_name,
                        attempts,
                        exc,
                    )
                    continue

                context.analysis.status = AnalysisStatus.FAILED
                context.analysis.error = f"{type(exc).__name__}: {exc}"
                self._engine.provenance.finalize(run_id)
                logger.error(
                    "step %d (%s) failed after %d attempt(s), checkpoint preserved for resume: %s",
                    index,
                    step_name,
                    attempts,
                    exc,
                )
                raise WorkflowError(
                    f"Workflow '{context.analysis.workflow_name}' failed at step {index} "
                    f"({step_name}) after {attempts} attempt(s): {exc}. A checkpoint has "
                    f"been preserved -- call run() again with the same run_id to resume "
                    f"from the last completed step."
                ) from exc
