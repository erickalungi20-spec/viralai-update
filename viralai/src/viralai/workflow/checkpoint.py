"""
Checkpoint Manager (Blueprint Ch.17.6: "automatic checkpointing, module retries,
graceful error handling, partial workflow recovery").

Persists workflow progress after every successful step, so a workflow interrupted by a
crash, a transient error, or a deliberate stop can resume from the last completed step
instead of restarting from scratch. Checkpointed state is restricted to whatever a step
has written into `ctx.analysis.results` -- the same JSON-safe dict convention already
established in Phase 2's integration test -- because that's what makes "save it, reload
it, keep going" actually reliable rather than a best-effort pickle of arbitrary objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger

logger = get_logger("workflow.checkpoint")


@dataclass
class Checkpoint:
    workflow_run_id: str
    completed_step_index: int
    results: dict[str, Any]
    configuration: dict[str, Any]


class CheckpointManager:
    """File-backed checkpoint storage, one JSON file per workflow run id. Same pragmatic
    "real, tested, zero external infrastructure" pattern as every prior file-backed store
    in this codebase (Knowledge Base, Model Registry, Digital Laboratory Manager).
    """

    def __init__(self, storage_dir: Path | str) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> None:
        path = self._path_for(checkpoint.workflow_run_id)
        payload = {
            "workflow_run_id": checkpoint.workflow_run_id,
            "completed_step_index": checkpoint.completed_step_index,
            "results": checkpoint.results,
            "configuration": checkpoint.configuration,
        }
        try:
            serialized = json.dumps(payload, indent=2)
        except TypeError as exc:
            raise ValidationError(
                "Checkpoint results must be JSON-serializable -- a workflow step wrote a "
                "non-JSON-safe value into ctx.analysis.results. Convert it (e.g. "
                "model_dump(mode='json') for pydantic objects) before returning."
            ) from exc
        path.write_text(serialized, encoding="utf-8")
        logger.debug(
            "checkpoint saved: run=%s step=%d",
            checkpoint.workflow_run_id,
            checkpoint.completed_step_index,
        )

    def load(self, workflow_run_id: str) -> Checkpoint | None:
        path = self._path_for(workflow_run_id)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Checkpoint(
            workflow_run_id=raw["workflow_run_id"],
            completed_step_index=raw["completed_step_index"],
            results=raw["results"],
            configuration=raw["configuration"],
        )

    def clear(self, workflow_run_id: str) -> None:
        """Remove a checkpoint -- called once a workflow completes successfully. A
        completed workflow has no partial state left to resume from.
        """
        path = self._path_for(workflow_run_id)
        if path.exists():
            path.unlink()
            logger.debug("checkpoint cleared: run=%s", workflow_run_id)

    def exists(self, workflow_run_id: str) -> bool:
        return self._path_for(workflow_run_id).exists()

    def _path_for(self, workflow_run_id: str) -> Path:
        if not workflow_run_id or "/" in workflow_run_id or "\\" in workflow_run_id:
            raise ValidationError(f"Invalid workflow_run_id: {workflow_run_id!r}")
        return self._storage_dir / f"{workflow_run_id}.json"
