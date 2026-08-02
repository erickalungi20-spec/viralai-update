"""
AI API (Blueprint Ch.30.3 AI API): exposes prediction services against models already
trained and registered via Phase 4's AITrainingPipelineManager. This API does NOT train
models inline -- training is a deliberate, tracked pipeline operation, not an HTTP
request side effect.

Model/record listing (GET) is open. Prediction (POST, actually runs compute against a
model) requires RESEARCHER role and is audit-logged, and its response is wrapped in a
ResponsibleAIEnvelope (Ch.36) -- the research-use disclosure is structurally part of the
payload, not just accompanying prose.
"""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from viralai.ai.dataset_repository import DatasetExample, DatasetRepository
from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FEATURE_NAMES, FeatureContext
from viralai.ai.reasoning import ScientificReasoningEngine
from viralai.ai.registry import ModelRecord, ModelRegistry
from viralai.ai.training_pipeline import AITrainingPipelineManager
from viralai.api.auth import require_role
from viralai.api.dependencies import (
    get_audit_logger,
    get_dataset_repository,
    get_knowledge_base,
    get_model_registry,
)
from viralai.api.schemas import (
    ExplainabilityRequest,
    ExplainabilityResponse,
    ModelRecordResponse,
    PredictionRequest,
    PredictionResponse,
    ReasoningRequest,
    ReasoningResponse,
    RegisterTrainingDatasetRequest,
    TrainingDatasetRecordResponse,
    TrainModelFromDatasetRequest,
    TrainModelFromDatasetResponse,
)
from viralai.common.errors import ValidationError
from viralai.engines.protein_engine import ProteinAnalysisEngine
from viralai.graph import (
    ResearchGraph,
    ingest_knowledge_base,
    ingest_mutations,
    ingest_protein_mutations,
    ingest_virus_and_genes,
)
from viralai.knowledge.store import KnowledgeBase
from viralai.security.api_keys import APIKeyRecord
from viralai.security.audit import AuditLogger
from viralai.security.responsible_ai import ResponsibleAIEnvelope, wrap_ai_result
from viralai.security.roles import Role

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/models/demo/register")
def register_demo_model(
    registry=Depends(get_model_registry),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Register a tiny demo model via the existing training/registry APIs.

    This endpoint creates a deliberately-labeled demo model so the UI can show
    explainability options and a model selector without shipping any "real" model.
    """
    import numpy as np

    from viralai.ai.hotspot_model import MutationHotspotModel

    n_features = len(FEATURE_NAMES)
    # tiny synthetic dataset
    X = np.zeros((10, n_features), dtype=float)
    y = np.array([0, 1] * 5)
    model = MutationHotspotModel(n_estimators=5, random_state=0)
    metrics = model.train(X, y)

    record = registry.register(
        model,
        name="demo",
        version="0.0.1",
        training_metrics=metrics,
        training_sample_count=len(y),
        notes="Synthetic demo model; not for research claims",
    )
    audit.record(actor=api_key.label, action="ai.register_demo_model", resource="demo/0.0.1")
    return {"name": record.name, "version": record.version, "registered_at": record.registered_at.isoformat()}


@router.get("/models/{name}/versions", response_model=list[str])
def list_model_versions(
    name: str, registry: ModelRegistry = Depends(get_model_registry)
) -> list[str]:
    return registry.list_versions(name)


@router.get("/models/{name}/{version}", response_model=ModelRecord)
def get_model_record(
    name: str, version: str, registry: ModelRegistry = Depends(get_model_registry)
) -> ModelRecord:
    try:
        return registry.get_record(name, version)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/datasets", response_model=TrainingDatasetRecordResponse, status_code=201)
def register_training_dataset(
    request: RegisterTrainingDatasetRequest,
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
    api_key: APIKeyRecord = Depends(require_role(Role.ADMIN)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> TrainingDatasetRecordResponse:
    try:
        record = dataset_repository.register(
            name=request.name,
            version=request.version,
            description=request.description,
            training_examples=[
                DatasetExample.parse_obj(example.model_dump())
                for example in request.training_examples
            ],
            validation_examples=[
                DatasetExample.parse_obj(example.model_dump())
                for example in request.validation_examples
            ],
            validation_split=request.validation_split,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit.record(
        actor=api_key.label,
        action="ai.dataset.register",
        resource=f"{request.name}/{request.version}",
    )

    return TrainingDatasetRecordResponse(
        name=record.name,
        version=record.version,
        description=record.description,
        created_at=record.created_at.isoformat(),
        training_example_count=len(record.training_examples),
        validation_example_count=len(record.validation_examples),
        validation_split=record.validation_split,
        sample_count=record.sample_count,
        validation_count=record.validation_count,
    )


@router.get("/datasets", response_model=list[TrainingDatasetRecordResponse])
def list_training_datasets(
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> list[TrainingDatasetRecordResponse]:
    records: list[TrainingDatasetRecordResponse] = []
    for name in dataset_repository.list_dataset_names():
        for version in dataset_repository.list_versions(name):
            record = dataset_repository.get_record(name, version)
            records.append(
                TrainingDatasetRecordResponse(
                    name=record.name,
                    version=record.version,
                    description=record.description,
                    created_at=record.created_at.isoformat(),
                    training_example_count=len(record.training_examples),
                    validation_example_count=len(record.validation_examples),
                    validation_split=record.validation_split,
                    sample_count=record.sample_count,
                    validation_count=record.validation_count,
                )
            )
    return records


@router.get("/datasets/{name}/{version}", response_model=TrainingDatasetRecordResponse)
def get_training_dataset(
    name: str,
    version: str,
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> TrainingDatasetRecordResponse:
    try:
        record = dataset_repository.get_record(name, version)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return TrainingDatasetRecordResponse(
        name=record.name,
        version=record.version,
        description=record.description,
        created_at=record.created_at.isoformat(),
        training_example_count=len(record.training_examples),
        validation_example_count=len(record.validation_examples),
        validation_split=record.validation_split,
        sample_count=record.sample_count,
        validation_count=record.validation_count,
    )


@router.post(
    "/datasets/{name}/{version}/train",
    response_model=TrainModelFromDatasetResponse,
    status_code=201,
)
def train_model_from_dataset(
    name: str,
    version: str,
    request: TrainModelFromDatasetRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
    api_key: APIKeyRecord = Depends(require_role(Role.ADMIN)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> TrainModelFromDatasetResponse:
    try:
        dataset = dataset_repository.get_record(name, version)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pipeline = AITrainingPipelineManager(registry)
    training_examples = dataset.training_examples_as_labeled()
    validation_examples = dataset.validation_examples_as_labeled() if request.use_validation else None

    try:
        report = pipeline.run(
            name=request.model_name,
            version=request.model_version,
            training_examples=training_examples,
            validation_examples=validation_examples,
            notes=request.notes,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit.record(
        actor=api_key.label,
        action="ai.model.train_from_dataset",
        resource=f"{name}/{version}",
        details={
            "model_name": request.model_name,
            "model_version": request.model_version,
            "use_validation": request.use_validation,
            "sample_count": len(training_examples),
        },
    )

    return TrainModelFromDatasetResponse(
        model_record=ModelRecordResponse(
            name=report.model_record.name,
            version=report.model_record.version,
            registered_at=report.model_record.registered_at.isoformat(),
            training_metrics=report.model_record.training_metrics,
            feature_names=report.model_record.feature_names,
            training_sample_count=report.model_record.training_sample_count,
            model_type=report.model_record.model_type,
            notes=report.model_record.notes,
        ),
        training_metrics=report.training_metrics,
        validation_metrics=report.validation_metrics,
        feature_importances=report.feature_importances,
    )


@router.post(
    "/models/{name}/{version}/predict", response_model=ResponsibleAIEnvelope[PredictionResponse]
)
def predict(
    name: str,
    version: str,
    request: PredictionRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ResponsibleAIEnvelope[PredictionResponse]:
    try:
        model = registry.load_model(name, version)
    except ValidationError as exc:
        audit.record(
            actor=api_key.label, action="ai.predict", resource=f"{name}/{version}", outcome="error"
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    X = np.array(request.feature_vectors)
    predictions = [bool(p) for p in model.predict(X)]
    confidences = [float(c) for c in model.predict_proba(X)]

    audit.record(
        actor=api_key.label,
        action="ai.predict",
        resource=f"{name}/{version}",
        details={"sample_count": len(request.feature_vectors)},
    )
    return wrap_ai_result(PredictionResponse(predictions=predictions, confidences=confidences))


@router.post("/models/{name}/{version}/explain", response_model=ExplainabilityResponse)
def explain(
    name: str,
    version: str,
    request: ExplainabilityRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ExplainabilityResponse:
    try:
        model = registry.load_model(name, version)
    except ValidationError as exc:
        audit.record(actor=api_key.label, action="ai.explain", resource=f"{name}/{version}", outcome="error")
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not model.is_trained:
        audit.record(actor=api_key.label, action="ai.explain", resource=f"{name}/{version}", outcome="denied")
        raise HTTPException(status_code=400, detail="Model is not trained")

    vector = np.array(request.feature_vector, dtype=float).reshape(1, -1)
    explainer = ShapExplainer(model)
    top_features = explainer.top_features(vector[0], n=3)
    response = ExplainabilityResponse(
        top_features=[{"feature": feature, "value": float(value)} for feature, value in top_features],
        feature_names=FEATURE_NAMES,
    )
    audit.record(
        actor=api_key.label,
        action="ai.explain",
        resource=f"{name}/{version}",
        details={"feature_count": len(request.feature_vector)},
    )
    return response


@router.post(
    "/models/{name}/{version}/reason",
    response_model=ReasoningResponse,
)
def reason(
    name: str,
    version: str,
    request: ReasoningRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    knowledge_base: KnowledgeBase = Depends(get_knowledge_base),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ReasoningResponse:
    try:
        model = registry.load_model(name, version)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not model.is_trained:
        audit.record(actor=api_key.label, action="ai.reason", resource=f"{name}/{version}", outcome="denied")
        raise HTTPException(status_code=400, detail="Model is not trained")

    explainer = ShapExplainer(model)
    context = FeatureContext(
        genome_length=request.genome_length,
        entropy_at_position=request.entropy_at_position,
        population_frequency=request.population_frequency,
        protein_mutation=None,
    )

    protein_mutations: list = []
    if request.reference_genome and request.gene_annotations:
        protein_engine = ProteinAnalysisEngine()
        protein_mutations = protein_engine.analyze(
            request.reference_genome,
            [request.mutation],
            request.gene_annotations,
        )
        if protein_mutations:
            context.protein_mutation = protein_mutations[0]

    graph = ResearchGraph()
    if request.gene_annotations:
        ingest_virus_and_genes(graph, request.virus, request.gene_annotations)
    ingest_mutations(graph, request.virus, [request.mutation], request.gene_annotations)
    if protein_mutations:
        ingest_protein_mutations(graph, request.virus, protein_mutations)
    ingest_knowledge_base(graph, request.virus, knowledge_base)

    reasoning_engine = ScientificReasoningEngine(graph)
    record = reasoning_engine.reason(
        request.virus,
        request.mutation,
        context,
        model,
        explainer,
    )

    response = ReasoningResponse(
        virus=record.virus,
        mutation_summary=record.mutation_summary,
        affected_protein=record.affected_protein,
        literature_citations=record.literature_citations,
        evolutionary_conservation=record.evolutionary_conservation,
        ai_prediction_positive=record.ai_prediction_positive,
        ai_confidence=record.ai_confidence,
        top_contributing_features=[
            {"feature": feature, "value": float(value)}
            for feature, value in record.top_contributing_features
        ],
        evidence_level=record.evidence_level.value,
        recommendation=record.recommendation,
    )
    audit.record(
        actor=api_key.label,
        action="ai.reason",
        resource=f"{name}/{version}",
        details={"mutation": request.mutation, "virus": request.virus},
    )
    return response
