"""
Phase 7 Research Workspace: organizes a research project's datasets, workflow
executions, analysis results, reports, and research notebook as one persistent,
file-backed unit (Blueprint Ch.20).
"""

from viralai.workspace.models import (
    ProjectMetadata,
    ProjectStatus,
    ResearchNote,
    StatusHistoryEntry,
)
from viralai.workspace.workspace import ResearchWorkspace

__all__ = [
    "ResearchWorkspace",
    "ProjectMetadata",
    "ProjectStatus",
    "ResearchNote",
    "StatusHistoryEntry",
]
