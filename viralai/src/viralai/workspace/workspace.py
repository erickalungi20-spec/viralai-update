"""
Research Workspace (Blueprint Ch.20).

Turns ViralAI from "a set of engines you script against" into a digital laboratory where
a research project is a persistent, organized unit: datasets, workflow executions,
analysis results, reports, and a research notebook, all under one project directory.
File-backed, same pattern as every other registry in this codebase.
"""

from __future__ import annotations

import json
from pathlib import Path

from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger
from viralai.core.idm import Analysis
from viralai.reporting import exporters as report_exporters
from viralai.reporting.report_models import AnalysisReport
from viralai.workspace.models import (
    ProjectMetadata,
    ProjectStatus,
    ResearchNote,
    StatusHistoryEntry,
)

logger = get_logger("workspace")

_SUBDIRS = ("datasets", "workflows", "analyses", "reports", "notebook")


class ResearchWorkspace:
    """One project = one directory. Construct with `metadata` to create a new project,
    or omit it to load an existing one from `root_dir`.
    """

    def __init__(self, root_dir: Path | str, metadata: ProjectMetadata | None = None) -> None:
        self._root = Path(root_dir)

        if metadata is not None:
            if self._root.exists() and (self._root / "metadata.json").exists():
                raise ValidationError(f"A project already exists at {self._root}")
            self._root.mkdir(parents=True, exist_ok=True)
            for subdir in _SUBDIRS:
                (self._root / subdir).mkdir(exist_ok=True)
            self.metadata = metadata
            self._save_metadata()
            self._append_status_history(
                StatusHistoryEntry(status=metadata.status, note="project created")
            )
            logger.info("project created: %s (%s)", metadata.title, metadata.project_id)
        else:
            metadata_path = self._root / "metadata.json"
            if not metadata_path.exists():
                raise ValidationError(f"No project found at {self._root} (no metadata.json)")
            self.metadata = ProjectMetadata(**json.loads(metadata_path.read_text(encoding="utf-8")))
            logger.info("project loaded: %s (%s)", self.metadata.title, self.metadata.project_id)

    # -- lifecycle -------------------------------------------------------------------

    def set_status(self, status: ProjectStatus, note: str = "") -> None:
        self.metadata.status = status
        self._save_metadata()
        self._append_status_history(StatusHistoryEntry(status=status, note=note))
        logger.info("project %s status -> %s", self.metadata.project_id, status.value)

    def status_history(self) -> list[StatusHistoryEntry]:
        path = self._root / "status_history.jsonl"
        if not path.exists():
            return []
        return [
            StatusHistoryEntry(**json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    # -- workflow executions -----------------------------------------------------------

    def record_workflow_execution(self, analysis: Analysis) -> Path:
        from viralai.storage.utils import atomic_write_text

        path = self._root / "workflows" / f"{analysis.analysis_id}.json"
        atomic_write_text(path, analysis.model_dump_json(indent=2))
        return path

    def list_workflow_executions(self) -> list[str]:
        return sorted(p.stem for p in (self._root / "workflows").glob("*.json"))

    def get_workflow_execution(self, analysis_id: str) -> Analysis:
        path = self._root / "workflows" / f"{analysis_id}.json"
        if not path.exists():
            raise ValidationError(f"No workflow execution '{analysis_id}' in this project")
        return Analysis(**json.loads(path.read_text(encoding="utf-8")))

    # -- analysis results ----------------------------------------------------------------

    def store_analysis_result(self, name: str, data: dict) -> Path:
        from viralai.storage.utils import atomic_write_text

        path = self._root / "analyses" / f"{_safe(name)}.json"
        atomic_write_text(path, json.dumps(data, indent=2, default=str))
        return path

    def get_analysis_result(self, name: str) -> dict:
        path = self._root / "analyses" / f"{_safe(name)}.json"
        if not path.exists():
            raise ValidationError(f"No stored analysis result named '{name}' in this project")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_analyses(self) -> list[str]:
        return sorted(p.stem for p in (self._root / "analyses").glob("*.json"))

    # -- reports -------------------------------------------------------------------------

    def store_report(
        self, name: str, report: AnalysisReport, *, formats: tuple[str, ...] = ("markdown", "json")
    ) -> list[Path]:
        exporters = {
            "markdown": (report_exporters.to_markdown, "md"),
            "json": (report_exporters.to_json, "json"),
            "csv": (report_exporters.to_csv, "csv"),
            "html": (report_exporters.to_html, "html"),
        }
        written: list[Path] = []
        for fmt in formats:
            if fmt not in exporters:
                raise ValidationError(
                    f"Unknown report format '{fmt}', expected one of {list(exporters)}"
                )
            render, extension = exporters[fmt]
            path = self._root / "reports" / f"{_safe(name)}.{extension}"
            # Reports contain scientific symbols such as nucleotide diversity (π).
            # Use atomic write to avoid partial files on interruption.
            from viralai.storage.utils import atomic_write_text

            atomic_write_text(path, render(report))
            written.append(path)
        return written

    def list_reports(self) -> list[str]:
        return sorted(p.name for p in (self._root / "reports").glob("*") if p.is_file())

    # -- research notebook -----------------------------------------------------------------

    def add_research_note(
        self, content: str, *, author: str = "researcher", tags: list[str] | None = None
    ) -> ResearchNote:
        note = ResearchNote(content=content, author=author, tags=tags or [])
        path = self._root / "notebook" / "notes.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(note.model_dump_json() + "\n")
        return note

    def list_notes(self, *, tag: str | None = None) -> list[ResearchNote]:
        path = self._root / "notebook" / "notes.jsonl"
        if not path.exists():
            return []
        notes = [
            ResearchNote(**json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if tag:
            notes = [n for n in notes if tag in n.tags]
        return notes

    # -- internals -------------------------------------------------------------------------

    def _save_metadata(self) -> None:
        from viralai.storage.utils import atomic_write_text

        atomic_write_text((self._root / "metadata.json"), self.metadata.model_dump_json(indent=2))

    def _append_status_history(self, entry: StatusHistoryEntry) -> None:
        path = self._root / "status_history.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")


def _safe(value: str) -> str:
    if not value or "/" in value or "\\" in value or ".." in value:
        raise ValidationError(f"Invalid identifier: {value!r}")
    return value
