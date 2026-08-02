"""
Audit Logging (Blueprint Ch.35.3: "every significant action recorded, e.g. project
creation, dataset import, plugin installation, AI model execution, report generation").

Append-only, JSONL, same file-backed pattern as everything else in this codebase. Never
overwrites or deletes prior entries -- an audit log that can be edited after the fact
isn't an audit log.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from viralai.common.ids import new_id


class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: new_id("audit"))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str  # API key label/id, or "system" for internal operations
    action: str  # e.g. "knowledge.add_mutation", "simulation.run_experiment"
    resource: str  # what was acted on, e.g. "HPV16/E6/position-118"
    outcome: str  # "success" or "denied" or "error"
    details: dict = Field(default_factory=dict)


class AuditLogger:
    """Append-only audit trail. `record()` is the only write operation -- there is
    deliberately no update/delete method.
    """

    def __init__(self, storage_path: Path | str) -> None:
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        outcome: str = "success",
        details: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            actor=actor, action=action, resource=resource, outcome=outcome, details=details or {}
        )
        with self._storage_path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
        return entry

    def read_all(self) -> list[AuditEntry]:
        if not self._storage_path.exists():
            return []
        return [
            AuditEntry(**json.loads(line))
            for line in self._storage_path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    def read_for_actor(self, actor: str) -> list[AuditEntry]:
        return [entry for entry in self.read_all() if entry.actor == actor]
