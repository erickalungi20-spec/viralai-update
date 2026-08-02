from viralai.dashboard.models import DashboardSnapshot, ModuleStatus, PluginStatus


def test_modules_complete_count():
    snapshot = DashboardSnapshot(
        software_version="0.1.0",
        modules=[
            ModuleStatus(phase=0, name="A", complete=True),
            ModuleStatus(phase=1, name="B", complete=False),
        ],
    )
    assert snapshot.modules_complete_count == 1


def test_release_ready_false_with_no_modules():
    snapshot = DashboardSnapshot(software_version="0.1.0")
    assert snapshot.release_ready is False


def test_release_ready_false_when_a_module_incomplete():
    snapshot = DashboardSnapshot(
        software_version="0.1.0",
        modules=[
            ModuleStatus(phase=0, name="A", complete=True),
            ModuleStatus(phase=1, name="B", complete=False),
        ],
    )
    assert snapshot.release_ready is False


def test_release_ready_false_when_plugin_scan_dirty():
    snapshot = DashboardSnapshot(
        software_version="0.1.0",
        modules=[ModuleStatus(phase=0, name="A", complete=True)],
        plugins=[
            PluginStatus(
                name="p",
                version="0.1.0",
                certification_tier="experimental",
                security_scan_clean=False,
            )
        ],
    )
    assert snapshot.release_ready is False


def test_release_ready_false_when_benchmarks_not_all_passing():
    snapshot = DashboardSnapshot(
        software_version="0.1.0",
        modules=[ModuleStatus(phase=0, name="A", complete=True)],
        benchmark_datasets_total=5,
        benchmark_datasets_passing=3,
    )
    assert snapshot.release_ready is False


def test_release_ready_true_when_everything_passes():
    snapshot = DashboardSnapshot(
        software_version="0.1.0",
        modules=[ModuleStatus(phase=0, name="A", complete=True)],
        plugins=[
            PluginStatus(
                name="p",
                version="0.1.0",
                certification_tier="experimental",
                security_scan_clean=True,
            )
        ],
        benchmark_datasets_total=5,
        benchmark_datasets_passing=5,
    )
    assert snapshot.release_ready is True


def test_release_ready_true_when_no_benchmarks_run_yet():
    """Zero benchmarks total shouldn't itself block readiness -- that's a distinct
    signal (visible via benchmark_datasets_total==0 in the report) from "benchmarks ran
    and failed".
    """
    snapshot = DashboardSnapshot(
        software_version="0.1.0",
        modules=[ModuleStatus(phase=0, name="A", complete=True)],
        benchmark_datasets_total=0,
        benchmark_datasets_passing=0,
    )
    assert snapshot.release_ready is True
