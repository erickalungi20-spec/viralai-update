from viralai.benchmarking.repository import BenchmarkRepository


def test_run_and_record_returns_results(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")

    results = repo.run_and_record()

    assert len(results) > 0
    assert all(r.all_passed for r in results)


def test_history_accumulates_across_runs(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")

    repo.run_and_record()
    first_count = len(repo.history())
    repo.run_and_record()
    second_count = len(repo.history())

    assert second_count == first_count * 2


def test_history_persists_across_instances(tmp_path):
    path = tmp_path / "benchmarks.json"
    BenchmarkRepository(path).run_and_record()

    reloaded = BenchmarkRepository(path)
    assert len(reloaded.history()) > 0


def test_latest_run_returns_one_result_per_dataset(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")
    repo.run_and_record()
    repo.run_and_record()

    latest = repo.latest_run()
    dataset_ids = [r.dataset_id for r in latest]

    assert len(dataset_ids) == len(set(dataset_ids))  # no duplicates


def test_all_currently_passing_true_after_clean_run(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")
    repo.run_and_record()

    assert repo.all_currently_passing() is True


def test_all_currently_passing_false_when_no_runs_yet(tmp_path):
    repo = BenchmarkRepository(tmp_path / "benchmarks.json")
    assert repo.all_currently_passing() is False
