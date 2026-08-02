"""
Reporting API (Blueprint Ch.30.3 Reporting API): renders an AnalysisReport (built
client-side or by another endpoint's caller) into one of the Phase 6 export formats.
Stateless -- this does not persist anything; see the Research Workspace for that.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from viralai.reporting import exporters
from viralai.reporting.report_models import AnalysisReport

router = APIRouter(prefix="/reports", tags=["reports"])

_MEDIA_TYPES = {
    "markdown": "text/markdown",
    "json": "application/json",
    "csv": "text/csv",
    "html": "text/html",
}


@router.post("/export")
def export_report(report: AnalysisReport, format: str = "markdown") -> Response:  # noqa: A002
    if format not in _MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown format '{format}', expected one of {list(_MEDIA_TYPES)}",
        )

    render = {
        "markdown": exporters.to_markdown,
        "json": exporters.to_json,
        "csv": exporters.to_csv,
        "html": exporters.to_html,
    }[format]

    return PlainTextResponse(content=render(report), media_type=_MEDIA_TYPES[format])
