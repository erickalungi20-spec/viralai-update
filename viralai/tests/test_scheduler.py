import pytest

from viralai.core.scheduler import JobStatus, TaskScheduler


def test_submit_and_get_result():
    scheduler = TaskScheduler(max_workers=2)
    job = scheduler.submit(lambda x, y: x + y, 2, 3, name="add")

    result = scheduler.result(job.job_id, timeout=5)

    assert result == 5
    assert scheduler.status(job.job_id) == JobStatus.COMPLETED
    scheduler.shutdown()


def test_failed_job_status_and_error_captured():
    scheduler = TaskScheduler(max_workers=2)

    def will_fail():
        raise RuntimeError("simulation blew up")

    job = scheduler.submit(will_fail, name="failing-job")

    with pytest.raises(RuntimeError):
        scheduler.result(job.job_id, timeout=5)

    assert scheduler.status(job.job_id) == JobStatus.FAILED
    assert "simulation blew up" in scheduler.get_job(job.job_id).error
    scheduler.shutdown()


def test_multiple_jobs_run_independently():
    scheduler = TaskScheduler(max_workers=4)
    jobs = [scheduler.submit(lambda n=i: n * n, name=f"square-{i}") for i in range(5)]

    results = sorted(scheduler.result(j.job_id, timeout=5) for j in jobs)

    assert results == [0, 1, 4, 9, 16]
    scheduler.shutdown()
