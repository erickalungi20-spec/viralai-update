from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from viralai.api.dependencies import get_checkpoint_manager, get_core_engine, get_knowledge_base, get_workspaces_dir
from viralai.api.schemas import (
    TemplateRunRequest,
    WorkflowJobStatusResponse,
    WorkflowRunResponse,
    WorkflowTemplateField,
    WorkflowTemplateMetadata,
)
from viralai.common.ids import new_id
from viralai.knowledge.store import KnowledgeBase
from viralai.simulation.laboratory import DigitalLaboratoryManager
from viralai.simulation.population_simulator import SimulationConfig
from viralai.workflow import templates as workflow_templates
from viralai.workflow.runner import WorkflowRunner
from viralai.workspace.workspace import ResearchWorkspace

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/templates/metadata", response_model=list[WorkflowTemplateMetadata])
def list_template_metadata() -> list[WorkflowTemplateMetadata]:
    return [
        WorkflowTemplateMetadata(
            template="mutation_analysis",
            display_name="Mutation Analysis",
            description="Detect mutations between reference and sample genomes and classify protein impacts.",
            fields=[
                WorkflowTemplateField(name="reference_genome", label="Reference Genome", type="text", description="The reference genome sequence.", required=True),
                WorkflowTemplateField(name="query_genome", label="Query Genome", type="text", description="The query genome sequence.", required=True),
                WorkflowTemplateField(name="gene_annotations", label="Gene Annotations", type="json", description="Optional gene annotation metadata for protein analysis.", required=False),
            ],
        ),
        WorkflowTemplateMetadata(
            template="evolutionary_analysis",
            display_name="Evolutionary Analysis",
            description="Run mutation and protein analysis, then compute population diversity metrics.",
            fields=[
                WorkflowTemplateField(name="reference_genome", label="Reference Genome", type="text", description="The reference genome sequence.", required=True),
                WorkflowTemplateField(name="query_genome", label="Query Genome", type="text", description="The query genome sequence.", required=True),
                WorkflowTemplateField(name="gene_annotations", label="Gene Annotations", type="json", description="Optional gene annotation metadata for protein analysis.", required=False),
                WorkflowTemplateField(name="aligned_population", label="Aligned Population", type="json", description="A list of aligned genome sequences used to compute diversity.", required=True),
            ],
        ),
        WorkflowTemplateMetadata(
            template="pandemic_surveillance",
            display_name="Pandemic Surveillance",
            description="Detect hotspots across many samples and summarize surveillance metrics.",
            fields=[
                WorkflowTemplateField(name="reference_genome", label="Reference Genome", type="text", description="The reference genome sequence.", required=True),
                WorkflowTemplateField(name="query_genomes", label="Query Genomes", type="json", description="A list of sample genomes to scan for mutations.", required=True),
            ],
        ),
        WorkflowTemplateMetadata(
            template="cancer_research",
            display_name="Cancer Research",
            description="Mutation analysis plus oncogenic mutation knowledge lookup for a specific virus and gene.",
            fields=[
                WorkflowTemplateField(name="reference_genome", label="Reference Genome", type="text", description="The reference genome sequence.", required=True),
                WorkflowTemplateField(name="query_genome", label="Query Genome", type="text", description="The query genome sequence.", required=True),
                WorkflowTemplateField(name="gene_annotations", label="Gene Annotations", type="json", description="Optional gene annotation metadata for protein analysis.", required=False),
                WorkflowTemplateField(name="virus", label="Virus", type="text", description="The virus name to query knowledge for.", required=True),
                WorkflowTemplateField(name="gene", label="Gene", type="text", description="The gene name for knowledge lookup.", required=True),
            ],
        ),
        WorkflowTemplateMetadata(
            template="hiv_research",
            display_name="HIV Research",
            description="Evolutionary analysis plus HIV resistance knowledge lookup.",
            fields=[
                WorkflowTemplateField(name="reference_genome", label="Reference Genome", type="text", description="The reference genome sequence.", required=True),
                WorkflowTemplateField(name="query_genome", label="Query Genome", type="text", description="The query genome sequence.", required=True),
                WorkflowTemplateField(name="gene_annotations", label="Gene Annotations", type="json", description="Optional gene annotation metadata for protein analysis.", required=False),
                WorkflowTemplateField(name="aligned_population", label="Aligned Population", type="json", description="A list of aligned genome sequences used to compute diversity.", required=True),
                WorkflowTemplateField(name="virus", label="Virus", type="text", description="The HIV strain or virus name to query knowledge for.", required=True),
                WorkflowTemplateField(name="gene", label="Gene", type="text", description="The gene name for knowledge lookup.", required=True),
            ],
        ),
        WorkflowTemplateMetadata(
            template="simulation",
            display_name="Simulation",
            description="Run a laboratory simulation experiment and persist the result.",
            fields=[
                WorkflowTemplateField(name="name", label="Experiment Name", type="text", description="A unique name for the simulation.", required=True),
                WorkflowTemplateField(name="version", label="Version", type="text", description="A version identifier for the experiment.", required=True),
                WorkflowTemplateField(name="reference_genome", label="Reference Genome", type="text", description="The reference genome sequence.", required=True),
                WorkflowTemplateField(name="config", label="Simulation Config", type="json", description="Simulation config including population_size, generations, mutation_rate, seed.", required=True),
                WorkflowTemplateField(name="notes", label="Notes", type="text", description="Optional researcher notes.", required=False),
            ],
        ),
    ]


@router.post("/templates/run", response_model=WorkflowRunResponse)
def run_template(
    request: TemplateRunRequest,
    core=Depends(get_core_engine),
    checkpoint_manager=Depends(get_checkpoint_manager),
    workspaces_dir: Path = Depends(get_workspaces_dir),
    knowledge: KnowledgeBase = Depends(get_knowledge_base),
) -> dict[str, str]:
    template = request.template
    params = request.params or {}

    try:
        if template == "mutation_analysis":
            steps = workflow_templates.mutation_analysis_workflow(
                params["reference_genome"],
                params["query_genome"],
                params.get("gene_annotations", []),
            )
        elif template == "evolutionary_analysis":
            steps = workflow_templates.evolutionary_analysis_workflow(
                params["reference_genome"],
                params["query_genome"],
                params.get("gene_annotations", []),
                params.get("aligned_population", []),
            )
        elif template == "pandemic_surveillance":
            steps = workflow_templates.pandemic_surveillance_workflow(
                params["reference_genome"],
                params["query_genomes"],
            )
        elif template == "cancer_research":
            steps = workflow_templates.cancer_research_workflow(
                params["reference_genome"],
                params["query_genome"],
                params.get("gene_annotations", []),
                knowledge,
                params["virus"],
                params["gene"],
            )
        elif template == "hiv_research":
            steps = workflow_templates.hiv_research_workflow(
                params["reference_genome"],
                params["query_genome"],
                params.get("gene_annotations", []),
                params.get("aligned_population", []),
                knowledge,
                params["virus"],
                params["gene"],
            )
        elif template == "simulation":
            lab = DigitalLaboratoryManager(workspaces_dir / "simulations")
            config_raw = params.get("config", {})
            sim_config = SimulationConfig(**config_raw) if isinstance(config_raw, dict) else config_raw
            steps = workflow_templates.simulation_workflow(
                lab,
                name=params.get("name", "experiment"),
                version=params.get("version", "v1"),
                reference_genome=params["reference_genome"],
                config=sim_config,
                fitness_function=params.get("fitness_function"),
                notes=params.get("notes", ""),
            )
        else:
            raise ValueError("unknown template")
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing parameter: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = new_id("run")
    runs_dir = workspaces_dir / "workflow_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "template": template,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    def _run_and_persist_template() -> None:
        runner = WorkflowRunner(core, checkpoint_manager)
        analysis = runner.run(template, steps=steps, run_id=run_id)
        record_out = dict(record)
        record_out["status"] = "completed"
        record_out["analysis_id"] = analysis.analysis_id
        (runs_dir / f"{run_id}.json").write_text(json.dumps(record_out, indent=2), encoding="utf-8")

        if request.project_id:
            try:
                ws_path = workspaces_dir / request.project_id
                ws = ResearchWorkspace(ws_path)
                ws.record_workflow_execution(analysis)
            except Exception:
                pass

    job = core.scheduler.submit(_run_and_persist_template, name=f"template:{template}")
    record["job_id"] = job.job_id
    (runs_dir / f"{run_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {"run_id": run_id, "job_id": job.job_id}


@router.post("/{workflow_name}/run")
def start_workflow(
    workflow_name: str,
    configuration: dict | None = None,
    workspaces_dir: Path = Depends(get_workspaces_dir),
    core=Depends(get_core_engine),
    checkpoint_manager=Depends(get_checkpoint_manager),
):
    configuration = configuration or {}
    run_id = new_id("run")
    runs_dir = workspaces_dir / "workflow_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "workflow_name": workflow_name,
        "configuration": configuration,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    (runs_dir / f"{run_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    runner = WorkflowRunner(core, checkpoint_manager)

    def _demo_step(ctx) -> None:
        ctx.analysis.results["demo_result"] = {"message": "demo step completed"}

    def _run_and_persist() -> dict[str, str]:
        try:
            analysis = runner.run(workflow_name, steps=[_demo_step], configuration=configuration, run_id=run_id)
            record_out = dict(record)
            record_out["status"] = "completed"
            record_out["analysis_id"] = analysis.analysis_id
            (runs_dir / f"{run_id}.json").write_text(json.dumps(record_out, indent=2), encoding="utf-8")
            return {"run_id": run_id, "status": "completed", "analysis_id": analysis.analysis_id}
        except Exception as exc:
            record_out = dict(record)
            record_out["status"] = "failed"
            record_out["error"] = str(exc)
            (runs_dir / f"{run_id}.json").write_text(json.dumps(record_out, indent=2), encoding="utf-8")
            raise

    job = core.scheduler.submit(_run_and_persist, name=f"workflow:{workflow_name}")
    record["job_id"] = job.job_id
    (runs_dir / f"{run_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {"run_id": run_id, "status": "queued", "job_id": job.job_id}


@router.get("/runs")
def list_runs(workspaces_dir: Path = Depends(get_workspaces_dir)) -> list[dict]:
    runs_dir = workspaces_dir / "workflow_runs"
    if not runs_dir.exists():
        return []
    records: list[dict] = []
    for file_path in sorted(runs_dir.iterdir(), key=lambda p: p.name, reverse=True):
        if file_path.suffix != ".json":
            continue
        try:
            records.append(json.loads(file_path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return records


@router.get("/{run_id}")
def get_run(run_id: str, workspaces_dir: Path = Depends(get_workspaces_dir)) -> dict:
    runs_dir = workspaces_dir / "workflow_runs"
    path = runs_dir / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="run not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/jobs/{job_id}", response_model=WorkflowJobStatusResponse)
def get_job_status(job_id: str, core=Depends(get_core_engine)) -> dict[str, str | None]:
    try:
        job = core.scheduler.get_job(job_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    return {
        "job_id": job.job_id,
        "name": job.name,
        "status": job.status.value,
        "submitted_at": job.submitted_at.isoformat(),
        "error": job.error,
    }
