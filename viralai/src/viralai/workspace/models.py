"""
Research Workspace models (Blueprint Ch.20.3 Workspace Components, Ch.20.4 Project
Lifecycle).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from viralai.common.ids import new_id


class ProjectStatus(str, Enum):
    """Blueprint Ch.20.4 Project Lifecycle. Transitions are intentionally NOT enforced
    as a strict state machine here -- real research is not linear (a researcher may
    legitimately return from ANALYSIS to WORKFLOW_DESIGN to redesign an approach). The
    workspace records every transition in its status history regardless of direction;
    it doesn't police which transitions are "allowed".
    """

    CREATED = "created"
    DATA_IMPORTED = "data_imported"
    WORKFLOW_DESIGNED = "workflow_designed"
    ANALYSIS_RUNNING = "analysis_running"
    INTERPRETATION = "interpretation"
    VALIDATION = "validation"
    PUBLICATION = "publication"
    ARCHIVED = "archived"


class ProjectMetadata(BaseModel):
    project_id: str = Field(default_factory=lambda: new_id("project"))
    title: str
    research_objectives: str = ""
    principal_investigator: str = ""
    institution: str = ""
    collaborators: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ProjectStatus = ProjectStatus.CREATED


class StatusHistoryEntry(BaseModel):
    status: ProjectStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    note: str = ""


class ResearchNote(BaseModel):
    """Blueprint Ch.20.3 Research Notebook: hypotheses, observations, interpretation
    notes, future plans, meeting summaries -- free-text, tagged, append-only.
    """

    note_id: str = Field(default_factory=lambda: new_id("note"))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    author: str = "researcher"
    content: str
    tags: list[str] = Field(default_factory=list)
