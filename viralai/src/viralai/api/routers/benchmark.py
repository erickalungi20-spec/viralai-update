from __future__ import annotations

from fastapi import APIRouter, Depends

from viralai.api.auth import require_role
from viralai.api.dependencies import get_audit_logger, get_benchmark_repository
from viralai.benchmarking.datasets import all_benchmark_datasets
from viralai.benchmarking.models import BenchmarkDataset, BenchmarkResult
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.security.api_keys import APIKeyRecord
from viralai.security.audit import AuditLogger
from viralai.security.roles import Role

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get("/datasets", response_model=list[BenchmarkDataset])
def list_benchmark_datasets() -> list[BenchmarkDataset]:
    """List all available benchmark datasets supported by this installation."""
    return all_benchmark_datasets()


@router.post("/run", response_model=list[BenchmarkResult])
def run_benchmarks(
    repository: BenchmarkRepository = Depends(get_benchmark_repository),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> list[BenchmarkResult]:
    """Run all benchmark datasets and record the results."""
    try:
        results = repository.run_and_record()
    except Exception as exc:
        audit.record(actor=api_key.label, action="benchmark.run", resource="all", outcome="error", details={"error": str(exc)})
        raise
    audit.record(actor=api_key.label, action="benchmark.run", resource="all", details={"result_count": len(results)})
    return results


@router.get("/latest", response_model=list[BenchmarkResult])
def latest_benchmarks(repository: BenchmarkRepository = Depends(get_benchmark_repository)) -> list[BenchmarkResult]:
    """Return the latest benchmark run results."""
    return repository.latest_run()


@router.get("/history", response_model=list[BenchmarkResult])
def benchmark_history(repository: BenchmarkRepository = Depends(get_benchmark_repository)) -> list[BenchmarkResult]:
    """Return the full benchmark run history."""
    return repository.history()
