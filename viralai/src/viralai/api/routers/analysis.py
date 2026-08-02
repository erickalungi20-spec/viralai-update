"""
Analysis API (Blueprint Ch.30.3 Analysis API): mutation detection, protein
classification, and evolutionary summary as stateless HTTP operations directly over
Phase 2's engines. No persistence here -- see the Reporting API / Research Workspace for
that.
"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form
from typing import List
from pathlib import Path
import json
from time import monotonic
from datetime import datetime, timezone

from viralai.api.schemas import (
    EvolutionSummaryRequest,
    EvolutionSummaryResponse,
    MutationDetectionRequest,
    MutationDetectionResponse,
    ProteinAnalysisRequest,
    ProteinAnalysisResponse,
    EvaluateResponse,
    EvaluationReport,
)
from viralai.api.auth import require_role
from viralai.api.dependencies import get_data_root
from viralai.security.api_keys import APIKeyRecord
from viralai.security.roles import Role
from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.engines.mutation_engine import MutationEngine
from viralai.engines.protein_engine import ProteinAnalysisEngine
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.benchmarking.models import BenchmarkResult, BenchmarkMetric
import os
import json

router = APIRouter(prefix="/analysis", tags=["analysis"])

_mutation_engine = MutationEngine()
_protein_engine = ProteinAnalysisEngine()
_evolution_engine = EvolutionAnalysisEngine()


@router.post("/mutations", response_model=MutationDetectionResponse)
def detect_mutations(request: MutationDetectionRequest) -> MutationDetectionResponse:
    mutations = _mutation_engine.detect_mutations(request.reference_genome, request.query_genome)
    return MutationDetectionResponse(mutations=mutations)


@router.post("/proteins", response_model=ProteinAnalysisResponse)
def analyze_proteins(request: ProteinAnalysisRequest) -> ProteinAnalysisResponse:
    protein_mutations = _protein_engine.analyze(
        request.reference_genome, request.mutations, request.gene_annotations
    )
    return ProteinAnalysisResponse(protein_mutations=protein_mutations)


@router.post("/evolution", response_model=EvolutionSummaryResponse)
def evolution_summary(request: EvolutionSummaryRequest) -> EvolutionSummaryResponse:
    diversity = _evolution_engine.nucleotide_diversity(request.aligned_population)
    entropies = _evolution_engine.shannon_entropy_per_position(request.aligned_population)
    mean_entropy = sum(entropies) / len(entropies) if entropies else 0.0
    hotspots = [i for i, e in enumerate(entropies) if e >= request.hotspot_entropy_threshold]

    return EvolutionSummaryResponse(
        population_size=len(request.aligned_population),
        nucleotide_diversity=diversity,
        mean_entropy=mean_entropy,
        hotspot_positions=hotspots,
    )


def _parse_fasta_text(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l and not l.startswith(">")]
    return "".join(lines).upper()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_fasta(
    reference: UploadFile = File(...),
    queries: List[UploadFile] = File(...),
    expected_positions: str | None = Form(None),
    data_root: Path = Depends(get_data_root),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
) -> EvaluateResponse:
    """Evaluate mutation detection for a reference FASTA and one-or-more query FASTA uploads.

    Uploads must be FASTA-like text files. Returns per-query concise reports.
    """
    try:
        ref_text = (await reference.read()).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to read reference upload") from exc

    if ">" not in ref_text:
        raise HTTPException(status_code=400, detail="Reference upload does not appear to be FASTA")

    reference_seq = _parse_fasta_text(ref_text)
    engine = MutationEngine()
    reports: list[EvaluationReport] = []

    for q in queries:
        try:
            q_text = (await q.read()).decode("utf-8")
        except Exception:
            raise HTTPException(status_code=400, detail=f"Unable to read query file {q.filename}")
        if ">" not in q_text:
            raise HTTPException(status_code=400, detail=f"Query file {q.filename} does not appear to be FASTA")
        query_seq = _parse_fasta_text(q_text)
        start = monotonic()
        mutations = engine.detect_mutations(reference_seq, query_seq)
        elapsed = monotonic() - start
        report = EvaluationReport(
            reference=reference.filename,
            query=q.filename,
            mutation_count=len(mutations),
            positions=[m.position for m in mutations],
            runtime_seconds=elapsed,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        reports.append(report)

    # If expected positions supplied as JSON map {filename: [pos,...]}, compute simple metrics
    if expected_positions:
        try:
            expected_map = json.loads(expected_positions)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON for expected_positions")

        metrics_results: list[BenchmarkResult] = []
        for r in reports:
            expected = expected_map.get(r.query, []) or []
            detected = r.positions or []
            tp = len(set(detected) & set(expected))
            precision = tp / len(detected) if detected else 0.0
            recall = tp / len(expected) if expected else 0.0
            metrics = [
                BenchmarkMetric(metric_name="precision", expected=1.0, actual=precision, tolerance=0.0, passed=precision >= 1.0),
                BenchmarkMetric(metric_name="recall", expected=1.0, actual=recall, tolerance=0.0, passed=recall >= 1.0),
            ]
            result = BenchmarkResult(dataset_id=r.query, dataset_name=r.query, software_version=os.environ.get("VIRALAI_SOFTWARE_VERSION", "dev"), metrics=metrics)
            metrics_results.append(result)

        # Persist benchmark results if a repository path is available under data_root
        try:
            bench_path = Path(data_root) / "benchmarks.json"
            repo = BenchmarkRepository(bench_path)
            repo._append(metrics_results)
        except Exception:
            # Don't fail the evaluation if benchmarking persistence fails; just log
            import logging

            logging.getLogger("viralai.api.routers.analysis").exception("Failed to persist benchmark results")

    return EvaluateResponse(reports=reports)
