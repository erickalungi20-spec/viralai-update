from viralai.reporting.report_models import (
    AnalysisReport,
    MutationReportEntry,
    ReportProvenance,
    SimulationReportSection,
)


def _provenance() -> ReportProvenance:
    return ReportProvenance(software_version="0.1.0", virus="TestVirus")


def test_report_with_no_ai_or_simulation_content_does_not_require_disclaimer():
    report = AnalysisReport(
        title="Test",
        provenance=_provenance(),
        mutations=[
            MutationReportEntry(
                position=1,
                reference_base="A",
                observed_base="T",
                mutation_type="substitution",
                confidence_score=1.0,
            )
        ],
    )
    assert report.is_research_use_disclaimer_required is False


def test_report_with_ai_flagged_mutation_requires_disclaimer():
    report = AnalysisReport(
        title="Test",
        provenance=_provenance(),
        mutations=[
            MutationReportEntry(
                position=1,
                reference_base="A",
                observed_base="T",
                mutation_type="substitution",
                confidence_score=1.0,
                ai_flagged_as_hotspot=True,
            )
        ],
    )
    assert report.is_research_use_disclaimer_required is True


def test_report_with_simulation_section_requires_disclaimer():
    report = AnalysisReport(
        title="Test",
        provenance=_provenance(),
        simulations=[
            SimulationReportSection(
                experiment_name="exp",
                experiment_version="0.1.0",
                generations_run=5,
                extinction_generation=None,
                final_mean_mutations_from_reference=1.2,
            )
        ],
    )
    assert report.is_research_use_disclaimer_required is True
