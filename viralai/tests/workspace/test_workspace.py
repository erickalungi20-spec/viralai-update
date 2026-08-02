import pytest

from viralai.common.errors import ValidationError
from viralai.core.idm import Analysis, AnalysisStatus
from viralai.reporting.report_models import AnalysisReport, ReportProvenance
from viralai.workspace.models import ProjectMetadata, ProjectStatus
from viralai.workspace.workspace import ResearchWorkspace


def test_create_project_creates_directory_structure(tmp_path):
    root = tmp_path / "project1"
    metadata = ProjectMetadata(title="Test Project", principal_investigator="Dr. Test")

    workspace = ResearchWorkspace(root, metadata)

    assert (root / "metadata.json").exists()
    for subdir in ("datasets", "workflows", "analyses", "reports", "notebook"):
        assert (root / subdir).is_dir()
    assert workspace.metadata.title == "Test Project"
    assert workspace.metadata.status == ProjectStatus.CREATED


def test_cannot_create_project_where_one_already_exists(tmp_path):
    root = tmp_path / "project1"
    ResearchWorkspace(root, ProjectMetadata(title="First"))

    with pytest.raises(ValidationError):
        ResearchWorkspace(root, ProjectMetadata(title="Second"))


def test_load_existing_project(tmp_path):
    root = tmp_path / "project1"
    ResearchWorkspace(root, ProjectMetadata(title="Original Title", institution="MUST"))

    reloaded = ResearchWorkspace(root)

    assert reloaded.metadata.title == "Original Title"
    assert reloaded.metadata.institution == "MUST"


def test_loading_nonexistent_project_raises(tmp_path):
    with pytest.raises(ValidationError):
        ResearchWorkspace(tmp_path / "nonexistent")


def test_set_status_updates_metadata_and_history(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))

    workspace.set_status(ProjectStatus.DATA_IMPORTED, note="uploaded HPV16 samples")

    assert workspace.metadata.status == ProjectStatus.DATA_IMPORTED
    history = workspace.status_history()
    assert len(history) == 2  # initial "created" + this transition
    assert history[-1].status == ProjectStatus.DATA_IMPORTED
    assert history[-1].note == "uploaded HPV16 samples"


def test_status_persists_across_reload(tmp_path):
    root = tmp_path / "p"
    workspace = ResearchWorkspace(root, ProjectMetadata(title="Test"))
    workspace.set_status(ProjectStatus.ANALYSIS_RUNNING)

    reloaded = ResearchWorkspace(root)

    assert reloaded.metadata.status == ProjectStatus.ANALYSIS_RUNNING


def test_record_and_list_workflow_executions(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))
    analysis = Analysis(
        analysis_id="run-1", workflow_name="mutation-analysis", status=AnalysisStatus.COMPLETED
    )

    workspace.record_workflow_execution(analysis)

    assert workspace.list_workflow_executions() == ["run-1"]
    loaded = workspace.get_workflow_execution("run-1")
    assert loaded.workflow_name == "mutation-analysis"


def test_get_unknown_workflow_execution_raises(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))
    with pytest.raises(ValidationError):
        workspace.get_workflow_execution("nonexistent")


def test_store_and_get_analysis_result(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))

    workspace.store_analysis_result("mutation-summary", {"count": 5, "positions": [1, 2, 3]})

    assert "mutation-summary" in workspace.list_analyses()
    result = workspace.get_analysis_result("mutation-summary")
    assert result["count"] == 5


def test_store_report_writes_requested_formats(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))
    report = AnalysisReport(
        title="Test Report",
        provenance=ReportProvenance(software_version="0.1.0", virus="TestVirus"),
    )

    paths = workspace.store_report(
        "first-report", report, formats=("markdown", "json", "csv", "html")
    )

    assert len(paths) == 4
    for path in paths:
        assert path.exists()
    report_names = workspace.list_reports()
    assert "first-report.md" in report_names
    assert "first-report.json" in report_names
    assert "first-report.csv" in report_names
    assert "first-report.html" in report_names


def test_store_report_uses_utf8_for_scientific_symbols(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))
    report = AnalysisReport(
        title="Nucleotide diversity π",
        provenance=ReportProvenance(software_version="0.1.0", virus="TestVirus"),
    )

    path = workspace.store_report("unicode-report", report, formats=("markdown",))[0]

    assert "π" in path.read_text(encoding="utf-8")


def test_store_report_rejects_unknown_format(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))
    report = AnalysisReport(
        title="Test Report",
        provenance=ReportProvenance(software_version="0.1.0", virus="TestVirus"),
    )
    with pytest.raises(ValidationError):
        workspace.store_report("bad-report", report, formats=("pdf",))


def test_add_and_list_research_notes(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))

    workspace.add_research_note(
        "Hypothesis: E6 position 118 is a hotspot", tags=["hypothesis", "E6"]
    )
    workspace.add_research_note("Meeting notes from supervisor discussion", tags=["meeting"])

    all_notes = workspace.list_notes()
    assert len(all_notes) == 2

    hypothesis_notes = workspace.list_notes(tag="hypothesis")
    assert len(hypothesis_notes) == 1
    assert "E6 position 118" in hypothesis_notes[0].content


def test_notes_persist_across_reload(tmp_path):
    root = tmp_path / "p"
    workspace = ResearchWorkspace(root, ProjectMetadata(title="Test"))
    workspace.add_research_note("A persistent note")

    reloaded = ResearchWorkspace(root)

    assert len(reloaded.list_notes()) == 1
    assert reloaded.list_notes()[0].content == "A persistent note"


def test_unsafe_identifiers_rejected(tmp_path):
    workspace = ResearchWorkspace(tmp_path / "p", ProjectMetadata(title="Test"))
    with pytest.raises(ValidationError):
        workspace.store_analysis_result("../escape", {})
