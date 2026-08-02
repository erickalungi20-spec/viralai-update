"""Research Workspace API.

The workflow and workspace modules already provide project persistence for Python users.
This router exposes a deliberately small HTTP surface for the browser: create and browse
projects, then save/retrieve JSON-safe analysis outputs. Writes are researcher-only and
audited; project reads remain open like the platform's other reference data endpoints.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from viralai import __version__
from viralai.api.auth import require_role
from viralai.api.dependencies import get_audit_logger, get_core_engine, get_workspaces_dir
from viralai.api.schemas import (
    CreateWorkspaceRequest,
    SaveWorkspaceAnalysisRequest,
    SavedWorkspaceAnalysis,
    WorkspaceReportGenerationResponse,
)
from viralai.common.errors import ValidationError
from viralai.core.idm import Analysis, AnalysisStatus
from viralai.engines.mutation_engine import MutationEngine
from viralai.reporting.report_models import AnalysisReport, ReportProvenance
from viralai.security.api_keys import APIKeyRecord
from viralai.security.audit import AuditLogger
from viralai.security.roles import Role
from viralai.workspace.models import ProjectMetadata, ProjectStatus
from viralai.workspace.workspace import ResearchWorkspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

_PROJECT_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


@router.post("", response_model=ProjectMetadata, status_code=status.HTTP_201_CREATED)
def create_workspace(
    request: CreateWorkspaceRequest,
    workspaces_dir: Path = Depends(get_workspaces_dir),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ProjectMetadata:
    """Create one research project under the API-managed workspace root."""
    metadata = ProjectMetadata(
        title=request.title,
        research_objectives=request.research_objectives,
        principal_investigator=request.principal_investigator,
        institution=request.institution,
        collaborators=request.collaborators,
    )
    try:
        ResearchWorkspace(_workspace_path(workspaces_dir, metadata.project_id), metadata=metadata)
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    audit.record(actor=api_key.label, action="workspace.create", resource=metadata.project_id)
    return metadata


@router.get("", response_model=list[ProjectMetadata])
def list_workspaces(workspaces_dir: Path = Depends(get_workspaces_dir)) -> list[ProjectMetadata]:
    """List persisted projects, newest first, without requiring an API key."""
    if not workspaces_dir.exists():
        return []

    workspaces: list[ProjectMetadata] = []
    for candidate in workspaces_dir.iterdir():
        metadata_path = candidate / "metadata.json"
        if not candidate.is_dir() or not metadata_path.is_file():
            continue
        try:
            workspace = ResearchWorkspace(candidate)
        except (ValidationError, ValueError):
            continue
        workspaces.append(workspace.metadata)
    return sorted(workspaces, key=lambda workspace: workspace.created_at, reverse=True)


@router.get("/{project_id}", response_model=ProjectMetadata)
def get_workspace(
    project_id: str, workspaces_dir: Path = Depends(get_workspaces_dir)
) -> ProjectMetadata:
    return _load_workspace(workspaces_dir, project_id).metadata


@router.get("/{project_id}/analyses", response_model=list[str])
def list_workspace_analyses(
    project_id: str, workspaces_dir: Path = Depends(get_workspaces_dir)
) -> list[str]:
    return _load_workspace(workspaces_dir, project_id).list_analyses()


@router.post(
    "/{project_id}/analyses", response_model=SavedWorkspaceAnalysis, status_code=status.HTTP_201_CREATED
)
def save_workspace_analysis(
    project_id: str,
    request: SaveWorkspaceAnalysisRequest,
    workspaces_dir: Path = Depends(get_workspaces_dir),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> SavedWorkspaceAnalysis:
    """Persist a JSON-safe analysis payload in a project workspace."""
    workspace = _load_workspace(workspaces_dir, project_id)
    try:
        workspace.store_analysis_result(request.name, request.data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit.record(
        actor=api_key.label,
        action="workspace.store_analysis",
        resource=f"{project_id}/{request.name}",
    )
    return SavedWorkspaceAnalysis(project_id=project_id, name=request.name)


@router.get("/{project_id}/analyses/{name}", response_model=dict)
def get_workspace_analysis(
    project_id: str, name: str, workspaces_dir: Path = Depends(get_workspaces_dir)
) -> dict:
    workspace = _load_workspace(workspaces_dir, project_id)
    try:
        return workspace.get_analysis_result(name)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/comparisons")
async def create_comparison(
    project_id: str,
    reference_genome: str = Form(..., min_length=1),
    file: UploadFile = File(...),
    workspaces_dir: Path = Depends(get_workspaces_dir),
    core=Depends(get_core_engine),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict[str, str]:
    """Queue a background comparison of an uploaded FASTA sequence against a reference genome."""
    workspace = _load_workspace(workspaces_dir, project_id)
    filename = _safe_filename(file.filename or "uploaded_sequence.fasta")

    if not filename.lower().endswith((".fasta", ".fa", ".txt")):
        raise HTTPException(status_code=400, detail="Only FASTA-like text files are accepted.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 text.") from exc

    if ">" not in text:
        raise HTTPException(status_code=400, detail="Uploaded file does not contain FASTA header data.")

    dataset_dir = workspace._root / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    target_path = dataset_dir / filename
    target_path.write_text(text, encoding="utf-8")

    analysis_name = "uploaded-comparison"

    def _run_comparison() -> None:
        query_sequence = _extract_sequence(text)
        mutations = MutationEngine().detect_mutations(reference_genome, query_sequence)
        payload = {
            "filename": filename,
            "reference_genome": reference_genome,
            "query_genome": query_sequence,
            "mutations": [mutation.model_dump(mode="json") for mutation in mutations],
        }
        workspace.store_analysis_result(analysis_name, payload)
        workspace.set_status(ProjectStatus.ANALYSIS_RUNNING, note="comparison complete")

    job = core.scheduler.submit(_run_comparison, name=f"comparison:{project_id}")
    audit.record(
        actor=api_key.label,
        action="workspace.compare_upload",
        resource=f"{project_id}/{filename}",
        details={"analysis_name": analysis_name},
    )
    return {
        "status": "queued",
        "project_id": project_id,
        "analysis_name": analysis_name,
        "job_id": job.job_id,
        "filename": filename,
    }


@router.get("/{project_id}/comparisons/{analysis_name}")
def get_comparison_status(
    project_id: str,
    analysis_name: str,
    workspaces_dir: Path = Depends(get_workspaces_dir),
    core=Depends(get_core_engine),
) -> dict[str, str | None]:
    """Report the current state of a queued comparison job and any stored artifact."""
    workspace = _load_workspace(workspaces_dir, project_id)
    if analysis_name != "uploaded-comparison":
        raise HTTPException(status_code=404, detail=f"No comparison '{analysis_name}' in workspace '{project_id}'.")

    # The comparison job is tracked by the scheduler, but the workspace analysis payload
    # is stored once the job completes. This endpoint is intentionally lightweight and
    # returns the workspace's current state so the UI can poll it without blocking.
    if workspace.list_analyses() and analysis_name in workspace.list_analyses():
        payload = workspace.get_analysis_result(analysis_name)
        return {
            "project_id": project_id,
            "analysis_name": analysis_name,
            "status": "completed",
            "filename": payload.get("filename"),
            "job_id": None,
        }

    # Fall back to the scheduler if the job is still pending.
    try:
        job = core.scheduler.get_job(next(job_id for job_id in core.scheduler._jobs if core.scheduler._jobs[job_id].name == f"comparison:{project_id}"))
    except (StopIteration, KeyError):
        return {
            "project_id": project_id,
            "analysis_name": analysis_name,
            "status": "queued",
            "filename": None,
            "job_id": None,
        }

    return {
        "project_id": project_id,
        "analysis_name": analysis_name,
        "status": job.status.value,
        "filename": None,
        "job_id": job.job_id,
    }


@router.post("/{project_id}/reports/{report_name}/generate", response_model=WorkspaceReportGenerationResponse)
def generate_report(
    project_id: str,
    report_name: str,
    from_analysis: str | None = None,
    from_workflow: str | None = None,
    formats: list[str] | None = None,
    workspaces_dir: Path = Depends(get_workspaces_dir),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Generate and persist a report from a stored analysis or workflow execution.

    This is intentionally minimal: it synthesizes an AnalysisReport with provenance
    and any available mutation/evolution sections copied from stored analysis results.
    """
    workspace = _load_workspace(workspaces_dir, project_id)
    formats = tuple(formats or ["markdown", "json"])

    provenance = ReportProvenance(software_version=__version__, virus="unknown")
    report = AnalysisReport(title=report_name, provenance=provenance)

    if from_analysis:
        data = workspace.get_analysis_result(from_analysis)
        # best-effort: if the analysis contains 'mutations' or 'evolution', copy them
        if isinstance(data, dict):
            if "mutations" in data:
                report.mutations = data.get("mutations", [])
            if "evolution" in data:
                report.evolution = data.get("evolution")

    if from_workflow and not report.mutations:
        try:
            analysis = workspace.get_workflow_execution(from_workflow)
            raw = analysis.model_dump()
            if "results" in raw and isinstance(raw["results"], dict):
                results = raw["results"]
                if "mutations" in results:
                    report.mutations = results["mutations"]
        except ValidationError:
            pass

    written = workspace.store_report(report_name, report, formats=formats)
    report_urls = [f"/workspaces/{project_id}/reports/{p.name}" for p in written]
    audit.record(actor=api_key.label, action="workspace.generate_report", resource=f"{project_id}/{report_name}", details={"formats": list(formats)})
    return WorkspaceReportGenerationResponse(project_id=project_id, report_name=report_name, report_urls=report_urls)


@router.get("/{project_id}/reports/{filename}", response_class=FileResponse)
def download_workspace_report(
    project_id: str,
    filename: str,
    workspaces_dir: Path = Depends(get_workspaces_dir),
) -> FileResponse:
    workspace = _load_workspace(workspaces_dir, project_id)
    safe_name = _safe(filename)
    path = workspace._root / "reports" / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Report '{filename}' not found in workspace '{project_id}'.")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)


def _load_workspace(workspaces_dir: Path, project_id: str) -> ResearchWorkspace:
    if not _PROJECT_ID_PATTERN.fullmatch(project_id):
        raise HTTPException(status_code=404, detail=f"No workspace '{project_id}'")
    try:
        return ResearchWorkspace(_workspace_path(workspaces_dir, project_id))
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=f"No workspace '{project_id}'") from exc


def _workspace_path(workspaces_dir: Path, project_id: str) -> Path:
    """Construct a child path only after the identifier has been constrained."""
    if not _PROJECT_ID_PATTERN.fullmatch(project_id):
        raise HTTPException(status_code=404, detail=f"No workspace '{project_id}'")
    return workspaces_dir / project_id


def _safe_filename(filename: str) -> str:
    path = Path(filename).name
    safe = "".join(ch for ch in path if ch.isalnum() or ch in {"-", "_", "."})
    return safe or "uploaded_sequence.fasta"


def _extract_sequence(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sequence_lines = [line for line in lines if not line.startswith(">")]
    return "".join(sequence_lines)
