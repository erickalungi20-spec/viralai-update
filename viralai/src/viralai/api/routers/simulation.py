"""
Simulation API (Blueprint Ch.30.3 Simulation API): run and inspect Digital Laboratory
experiments over HTTP. Every response inherits `is_synthetic=True` from the underlying
SimulationExperiment -- the API does not strip that flag.

Running a simulation (POST, real compute cost) requires RESEARCHER role, is
audit-logged, and its response is wrapped in a ResponsibleAIEnvelope (Ch.36) --
structurally marking simulated data as synthetic and non-clinical, not just via the
existing is_synthetic field. Reading an already-run experiment (GET) is open.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from viralai.api.auth import require_role
from viralai.api.dependencies import get_audit_logger, get_simulation_lab
from viralai.api.schemas import RunSimulationRequest
from viralai.common.errors import ValidationError
from viralai.security.api_keys import APIKeyRecord
from viralai.security.audit import AuditLogger
from viralai.security.responsible_ai import ResponsibleAIEnvelope, wrap_simulation_result
from viralai.security.roles import Role
from viralai.simulation.laboratory import DigitalLaboratoryManager, SimulationExperiment
from viralai.simulation.population_simulator import SimulationConfig

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post(
    "/experiments", response_model=ResponsibleAIEnvelope[SimulationExperiment], status_code=201
)
def run_experiment(
    request: RunSimulationRequest,
    lab: DigitalLaboratoryManager = Depends(get_simulation_lab),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ResponsibleAIEnvelope[SimulationExperiment]:
    config = SimulationConfig(
        population_size=request.population_size,
        generations=request.generations,
        mutation_rate=request.mutation_rate,
        seed=request.seed,
    )
    resource = f"{request.name}/{request.version}"
    try:
        experiment = lab.run_experiment(
            name=request.name,
            version=request.version,
            reference_genome=request.reference_genome,
            config=config,
            notes=request.notes,
        )
    except ValidationError as exc:
        audit.record(
            actor=api_key.label,
            action="simulation.run_experiment",
            resource=resource,
            outcome="error",
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    audit.record(
        actor=api_key.label,
        action="simulation.run_experiment",
        resource=resource,
        details={"generations": request.generations, "population_size": request.population_size},
    )
    return wrap_simulation_result(experiment)


@router.get("/experiments/{name}/versions", response_model=list[str])
def list_experiment_versions(
    name: str, lab: DigitalLaboratoryManager = Depends(get_simulation_lab)
) -> list[str]:
    return lab.list_versions(name)


@router.get("/experiments/{name}/{version}", response_model=SimulationExperiment)
def get_experiment(
    name: str, version: str, lab: DigitalLaboratoryManager = Depends(get_simulation_lab)
) -> SimulationExperiment:
    try:
        return lab.get_experiment(name, version)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
