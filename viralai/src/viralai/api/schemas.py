"""
API request/response schemas.

Reuses IDM/report/knowledge/simulation models directly wherever they already fit
(they're pydantic already); adds thin request wrappers only where the API needs a shape
the internal models don't have (e.g. bundling reference + query genome together for a
detection request).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from viralai.core.idm import Genome, Mutation, ProteinMutation


class MutationDetectionRequest(BaseModel):
    reference_genome: str | Genome = Field(..., min_length=1)
    query_genome: str | Genome = Field(..., min_length=1)



class MutationDetectionResponse(BaseModel):
    mutations: list[Mutation]


class ProteinAnalysisRequest(BaseModel):
    reference_genome: str | Genome = Field(..., min_length=1)
    mutations: list[Mutation] = Field(..., min_length=1)
    gene_annotations: list[dict] = Field(default_factory=list)


class ProteinAnalysisResponse(BaseModel):
    protein_mutations: list[ProteinMutation]


class EvolutionSummaryRequest(BaseModel):
    aligned_population: list[str] = Field(..., min_length=2)
    hotspot_entropy_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class EvolutionSummaryResponse(BaseModel):
    population_size: int
    nucleotide_diversity: float
    mean_entropy: float
    hotspot_positions: list[int]


class PredictionRequest(BaseModel):
    feature_vectors: list[list[float]] = Field(..., min_length=1)

    @field_validator("feature_vectors", mode="after")
    def vector_not_empty(cls, feature_vectors: list[list[float]]) -> list[list[float]]:
        for vector in feature_vectors:
            if not vector:
                raise ValueError("Each feature vector must contain values")
        return feature_vectors


class PredictionResponse(BaseModel):
    predictions: list[bool]
    confidences: list[float]


class ExplainabilityRequest(BaseModel):
    feature_vector: list[float] = Field(..., min_length=1)


class FeatureImportance(BaseModel):
    feature: str
    value: float


class ExplainabilityResponse(BaseModel):
    top_features: list[FeatureImportance]
    feature_names: list[str]


class ReasoningRequest(BaseModel):
    virus: str = Field(..., min_length=1)
    mutation: Mutation
    reference_genome: str | Genome | None = None
    gene_annotations: list[dict] = Field(default_factory=list)
    genome_length: int = Field(default=0, ge=0)
    entropy_at_position: float = Field(default=0.0, ge=0.0, le=1.0)
    population_frequency: float = Field(default=0.0, ge=0.0, le=1.0)


class ReasoningResponse(BaseModel):
    virus: str
    mutation_summary: str
    affected_protein: str | None = None
    literature_citations: list[str]
    evolutionary_conservation: float | None = None
    ai_prediction_positive: bool
    ai_confidence: float
    top_contributing_features: list[FeatureImportance]
    evidence_level: str
    recommendation: str


class GenomicSearchResult(BaseModel):
    uid: str
    accession: str
    title: str
    organism: str | None = None
    taxonomy_id: int | None = None
    sequence_length: int | None = None
    pubdate: str | None = None
    update_date: str | None = None
    source: str
    source_url: str
    database: str | None = None
    download_url: str | None = None


class GenomicUploadResponse(BaseModel):
    filename: str
    path: str
    download_url: str
    message: str
    size_bytes: int


class GenomicImportResponse(BaseModel):
    filename: str
    path: str
    download_url: str
    accession: str
    uid: str
    organism: str | None = None
    title: str | None = None
    imported_at: str
    message: str
    size_bytes: int


class GenomicLibraryEntry(BaseModel):
    filename: str
    path: str
    download_url: str
    accession: str
    uid: str
    organism: str | None = None
    title: str | None = None
    imported_at: str
    size_bytes: int


class DatasetExampleRequest(BaseModel):
    mutation: Mutation
    context: dict[str, float] = Field(default_factory=dict)
    label: int = Field(..., ge=0, le=1)


class RegisterTrainingDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str = ""
    training_examples: list[DatasetExampleRequest] = Field(..., min_length=1)
    validation_examples: list[DatasetExampleRequest] = Field(default_factory=list)
    validation_split: float = Field(default=0.0, ge=0.0, le=1.0)


class TrainingDatasetRecordResponse(BaseModel):
    name: str
    version: str
    description: str
    created_at: str
    training_example_count: int
    validation_example_count: int
    validation_split: float
    sample_count: int
    validation_count: int


class TrainModelFromDatasetRequest(BaseModel):
    model_name: str = Field(..., min_length=1)
    model_version: str = Field(..., min_length=1)
    notes: str = ""
    use_validation: bool = True


class ModelRecordResponse(BaseModel):
    name: str
    version: str
    registered_at: str
    training_metrics: dict[str, float]
    feature_names: list[str]
    training_sample_count: int
    model_type: str
    notes: str = ""


class TrainModelFromDatasetResponse(BaseModel):
    model_record: ModelRecordResponse
    training_metrics: dict[str, float]
    validation_metrics: dict[str, float] | None
    feature_importances: dict[str, float]


class RunSimulationRequest(BaseModel):
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    reference_genome: str = Field(..., min_length=1)
    population_size: int = Field(..., gt=0)
    generations: int = Field(..., ge=0)
    mutation_rate: float = Field(..., ge=0.0, le=1.0)
    seed: int
    notes: str = ""


class WorkflowTemplateField(BaseModel):
    name: str
    label: str
    type: str
    description: str
    required: bool = True
    default: Any | None = None


class WorkflowTemplateMetadata(BaseModel):
    template: str
    display_name: str
    description: str
    fields: list[WorkflowTemplateField]


class TemplateRunRequest(BaseModel):
    template: Literal[
        "mutation_analysis",
        "evolutionary_analysis",
        "pandemic_surveillance",
        "cancer_research",
        "hiv_research",
        "simulation",
    ]
    params: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None

    @field_validator("params", mode="before")
    def params_must_be_dict(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("params must be an object")
        return value

    @model_validator(mode='after')
    def validate_template_params(self):
        template = self.template
        params = self.params or {}
        required_fields: dict[str, list[str]] = {
            "mutation_analysis": ["reference_genome", "query_genome"],
            "evolutionary_analysis": ["reference_genome", "query_genome", "aligned_population"],
            "pandemic_surveillance": ["reference_genome", "query_genomes"],
            "cancer_research": ["reference_genome", "query_genome", "virus", "gene"],
            "hiv_research": ["reference_genome", "query_genome", "aligned_population", "virus", "gene"],
            "simulation": ["reference_genome", "name", "version"],
        }
        missing = [field for field in required_fields.get(template, []) if field not in params]
        if missing:
            raise ValueError(f"Missing required params for {template}: {missing}")
        if template == "simulation":
            if "config" not in params or not isinstance(params.get("config"), dict):
                raise ValueError("Simulation template requires a config object")
        if template in {
            "mutation_analysis",
            "evolutionary_analysis",
            "cancer_research",
            "hiv_research",
        }:
            if params.get("reference_genome") == params.get("query_genome"):
                raise ValueError("reference_genome and query_genome must differ")
        return self


class WorkflowRunResponse(BaseModel):
    run_id: str
    job_id: str


class WorkflowJobStatusResponse(BaseModel):
    job_id: str
    name: str
    status: str
    submitted_at: str
    error: str | None = None


class CreateWorkspaceRequest(BaseModel):
    """The user-authored metadata required to start a research project."""

    title: str = Field(min_length=1, max_length=200)
    research_objectives: str = ""
    principal_investigator: str = ""
    institution: str = ""
    collaborators: list[str] = Field(default_factory=list)


class SaveWorkspaceAnalysisRequest(BaseModel):
    """A JSON-safe output from an API or workflow operation."""

    name: str = Field(min_length=1, max_length=160)
    data: dict[str, Any]


class SavedWorkspaceAnalysis(BaseModel):
    project_id: str
    name: str


class WorkspaceReportGenerationResponse(BaseModel):
    project_id: str
    report_name: str
    report_urls: list[str]


class ErrorResponse(BaseModel):
    detail: str


class EvaluationReport(BaseModel):
    reference: str
    query: str
    mutation_count: int
    positions: list[int]
    runtime_seconds: float
    timestamp: str


class EvaluateResponse(BaseModel):
    reports: list[EvaluationReport]
