"""
Phase 6 Reporting Engine: assembles AnalysisReport objects from Phase 2-5 output and
exports them to Markdown, JSON, CSV, and HTML.
"""

from viralai.reporting.exporters import (
    RESEARCH_USE_DISCLAIMER,
    to_csv,
    to_html,
    to_json,
    to_markdown,
)
from viralai.reporting.report_builder import ReportBuilder
from viralai.reporting.report_models import (
    AnalysisReport,
    EvolutionReportSection,
    MutationReportEntry,
    ReportProvenance,
    SimulationReportSection,
)

__all__ = [
    "ReportBuilder",
    "AnalysisReport",
    "ReportProvenance",
    "MutationReportEntry",
    "EvolutionReportSection",
    "SimulationReportSection",
    "to_markdown",
    "to_json",
    "to_csv",
    "to_html",
    "RESEARCH_USE_DISCLAIMER",
]
