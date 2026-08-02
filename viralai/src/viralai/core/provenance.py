"""
Provenance Manager.

Blueprint Addition 1 / Ch.15.3: every analysis must record software version, plugin
version, reference genome, parameters, and workflow history so another researcher could
reproduce it exactly. This module is the single place that builds that record — engines
report events, this assembles them into an Analysis's provenance trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from viralai.core.metadata import VIRALAI_SOFTWARE_VERSION
from viralai.common.logging import get_logger

logger = get_logger("core.provenance")


@dataclass
class ProvenanceRecord:
    analysis_id: str
    software_version: str = VIRALAI_SOFTWARE_VERSION
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    plugin_versions: dict[str, str] = field(default_factory=dict)

    def record_step(self, step_name: str, **details: Any) -> None:
        self.steps.append(
            {
                "step": step_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **details,
            }
        )
        logger.debug("provenance step recorded: analysis=%s step=%s", self.analysis_id, step_name)

    def finalize(self) -> None:
        self.finished_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "software_version": self.software_version,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "parameters": self.parameters,
            "plugin_versions": self.plugin_versions,
            "steps": self.steps,
        }


class ProvenanceManager:
    """Creates and stores ProvenanceRecords for every Analysis the Core Engine runs."""

    def __init__(self) -> None:
        self._records: dict[str, ProvenanceRecord] = {}

    def start(self, analysis_id: str, parameters: dict[str, Any] | None = None) -> ProvenanceRecord:
        record = ProvenanceRecord(analysis_id=analysis_id, parameters=parameters or {})
        self._records[analysis_id] = record
        return record

    def get(self, analysis_id: str) -> ProvenanceRecord:
        return self._records[analysis_id]

    def finalize(self, analysis_id: str) -> ProvenanceRecord:
        record = self._records[analysis_id]
        record.finalize()
        return record
