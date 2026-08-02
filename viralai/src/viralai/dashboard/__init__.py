"""
Phase 10 Development Dashboard (engineering review Recommendation 10): aggregates
module completion, plugin certification/security status, AI model performance,
benchmark status, and documentation coverage into one snapshot + Markdown report.
"""

from viralai.dashboard.builder import build_snapshot, to_markdown
from viralai.dashboard.collector import MODULE_PHASES
from viralai.dashboard.models import DashboardSnapshot, ModelStatus, ModuleStatus, PluginStatus

__all__ = [
    "build_snapshot",
    "to_markdown",
    "MODULE_PHASES",
    "DashboardSnapshot",
    "ModuleStatus",
    "PluginStatus",
    "ModelStatus",
]
