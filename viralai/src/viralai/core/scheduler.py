"""
Task Scheduler.

Simulations, AI retraining, and benchmark runs are long-running and shouldn't block the
caller. Phase 0 implementation uses a local thread pool (`concurrent.futures`) with a job
registry — no Celery/Redis broker required. It exposes the same job lifecycle (submit,
status, result, cancel-if-pending) that a Celery-backed scheduler will expose later — see
docs/adr/ADR-004-phase0-pragmatic-infrastructure.md. Call sites should depend on this
interface, not on threading specifics.
"""

from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from viralai.common.ids import new_id
from viralai.common.logging import get_logger

logger = get_logger("core.scheduler")


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    name: str
    status: JobStatus = JobStatus.QUEUED
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 0
    result: Any = None
    error: str | None = None
    _future: Future | None = field(default=None, repr=False, compare=False)


class TaskScheduler:
    """A local job queue with priority-aware submission and status tracking.

    Not a singleton — construct one per process/test, same reasoning as EventBus.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="viralai-job"
        )
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        name: str | None = None,
        priority: int = 0,
        **kwargs: Any,
    ) -> Job:
        """Queue `func(*args, **kwargs)` for background execution. Returns the Job handle
        immediately; use `status()` or `result()` to check progress.

        `priority` is recorded but Phase 0's ThreadPoolExecutor does not reorder on it —
        real prioritization requires a broker-backed queue (Celery), which is exactly the
        kind of thing that should wait for Phase 11 infrastructure, not be faked here.
        """
        job = Job(job_id=new_id("job"), name=name or func.__name__, priority=priority)
        with self._lock:
            self._jobs[job.job_id] = job

        def _run() -> Any:
            job.status = JobStatus.RUNNING
            logger.debug("job started id=%s name=%s", job.job_id, job.name)
            try:
                result = func(*args, **kwargs)
                job.result = result
                job.status = JobStatus.COMPLETED
                logger.debug("job completed id=%s name=%s", job.job_id, job.name)
                return result
            except Exception as exc:  # noqa: BLE001 - captured on the Job, not swallowed
                job.error = f"{type(exc).__name__}: {exc}"
                job.status = JobStatus.FAILED
                logger.exception("job failed id=%s name=%s", job.job_id, job.name)
                raise

        job._future = self._executor.submit(_run)
        return job

    def status(self, job_id: str) -> JobStatus:
        return self._jobs[job_id].status

    def result(self, job_id: str, timeout: float | None = None) -> Any:
        """Block until the job completes and return its result, or raise its exception."""
        job = self._jobs[job_id]
        assert job._future is not None
        return job._future.result(timeout=timeout)

    def get_job(self, job_id: str) -> Job:
        return self._jobs[job_id]

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
