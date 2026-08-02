"""
ViralAI API application (Blueprint Ch.30).

Mounting every router here means FastAPI's auto-generated OpenAPI schema (available at
/docs and /openapi.json) documents the whole surface for free -- this is what the
Commercial Development Workflow meant by "auto-generates OpenAPI docs... folds into
Phase 6's documentation engine for free": no separate hand-written API reference needed.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from viralai import __version__
from viralai.api.dependencies import (
    get_audit_logger,
    get_data_root,
    get_knowledge_base,
    get_model_registry,
    get_simulation_lab,
)
from viralai.api.routers import admin, ai, analysis, benchmark, genomic, knowledge, plugins, reports, simulation, workspaces, workflows
from viralai.common.errors import ConfigurationError
from viralai.plugins.loader import list_plugin_manifests
from viralai.security.encryption import validate_encryption_configuration

app = FastAPI(
    title="ViralAI API",
    description=(
        "AI-powered, modular, virus-agnostic viral genomics research and simulation "
        "platform. Research use only -- see /reports/export output and AI/simulation "
        "endpoints for the research-use disclaimer that applies to their results."
    ),
    version=__version__,
)

app.include_router(analysis.router)
app.include_router(plugins.router)
app.include_router(benchmark.router)
app.include_router(genomic.router)
app.include_router(knowledge.router)
app.include_router(ai.router)
app.include_router(simulation.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(workspaces.router)
app.include_router(workflows.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/ready", tags=["health"])
def readiness() -> JSONResponse:
    """Check the local dependencies needed to serve persisted API requests.

    This deliberately verifies the configured production encryption key without
    generating a development fallback. Database/broker checks will be added with the
    durable backend migration; the current release is a single-node file-backed service.
    """
    try:
        validate_encryption_configuration()
        get_knowledge_base()
        get_model_registry()
        get_simulation_lab()
        get_audit_logger()
    except (ConfigurationError, OSError) as exc:
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": str(exc)})
    return JSONResponse(content={"status": "ready", "version": __version__})


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/plugins/summary", tags=["plugins"])
def plugin_summary() -> JSONResponse:
    manifests = list_plugin_manifests(Path("plugins"))
    payload = [
        {
            "name": manifest.name,
            "version": manifest.version,
            "tier": manifest.certification_tier.value,
            "viruses": manifest.supported_viruses,
            "description": manifest.description,
            "reference_genome_accession": getattr(manifest, "reference_genome_accession", None),
        }
        for manifest in manifests
    ]
    return JSONResponse(payload)
