import csv
import io
import json

from viralai.reporting.exporters import (
    RESEARCH_USE_DISCLAIMER,
    to_csv,
    to_html,
    to_json,
    to_markdown,
)
from viralai.reporting.report_models import (
    AnalysisReport,
    EvolutionReportSection,
    MutationReportEntry,
    ReportProvenance,
)


def _sample_report() -> AnalysisReport:
    return AnalysisReport(
        title="HPV16 Test Analysis",
        provenance=ReportProvenance(
            software_version="0.1.0", virus="HPV16", plugin_name="hpv16", plugin_version="0.1.0"
        ),
        mutations=[
            MutationReportEntry(
                position=4,
                reference_base="A",
                observed_base="T",
                mutation_type="substitution",
                confidence_score=0.9,
                protein_classification="missense",
                ai_flagged_as_hotspot=True,
                ai_confidence=0.75,
                literature_citations=["publication:ref-1"],
            )
        ],
        evolution=EvolutionReportSection(
            population_size=5, nucleotide_diversity=0.12, mean_entropy=0.5, hotspot_positions=[4]
        ),
        summary_notes="Test summary notes.",
    )


def test_markdown_export_contains_key_sections():
    markdown = to_markdown(_sample_report())

    assert "# HPV16 Test Analysis" in markdown
    assert "## Mutations" in markdown
    assert "## Evolutionary Analysis" in markdown
    assert "A4T" in markdown
    assert RESEARCH_USE_DISCLAIMER in markdown


def test_json_export_round_trips_and_includes_disclaimer():
    payload = json.loads(to_json(_sample_report()))

    assert payload["title"] == "HPV16 Test Analysis"
    assert payload["mutations"][0]["position"] == 4
    assert payload["research_use_disclaimer"] == RESEARCH_USE_DISCLAIMER


def test_csv_export_has_one_row_per_mutation():
    csv_text = to_csv(_sample_report())
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["position"] == "4"
    assert rows[0]["protein_classification"] == "missense"


def test_csv_export_with_no_mutations_still_has_header():
    report = AnalysisReport(
        title="Empty", provenance=ReportProvenance(software_version="0.1.0", virus="TestVirus")
    )
    csv_text = to_csv(report)
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)

    assert "position" in header
    assert list(reader) == []


def test_html_export_is_valid_looking_and_contains_disclaimer():
    html = to_html(_sample_report())

    assert html.startswith("<!DOCTYPE html>")
    assert "<h1>HPV16 Test Analysis</h1>" in html
    assert "<table" in html
    assert RESEARCH_USE_DISCLAIMER in html


def test_html_export_escapes_report_content():
    report = _sample_report()
    report.title = "<script>alert('xss')</script>"
    report.provenance.virus = "<img src=x onerror=alert(1)>"

    rendered = to_html(report)

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;img src=x onerror=alert(1)&gt;" in rendered


def test_all_exporters_handle_a_minimal_report_with_no_optional_sections():
    minimal_report = AnalysisReport(
        title="Minimal", provenance=ReportProvenance(software_version="0.1.0", virus="TestVirus")
    )

    # none of these should raise
    to_markdown(minimal_report)
    to_json(minimal_report)
    to_csv(minimal_report)
    to_html(minimal_report)


def test_markdown_export_includes_reference_genome_accession_when_present():
    report = _sample_report()
    report.provenance.reference_genome_accession = "NC_001526.4"

    markdown = to_markdown(report)

    assert "NC_001526.4" in markdown


def test_markdown_export_renders_simulation_section_with_all_fields():
    from viralai.reporting.report_models import SimulationReportSection

    report = _sample_report()
    report.simulations.append(
        SimulationReportSection(
            experiment_name="drift-test",
            experiment_version="0.1.0",
            is_synthetic=True,
            generations_run=10,
            extinction_generation=7,
            final_mean_mutations_from_reference=3.5,
            notes="a test note",
        )
    )

    markdown = to_markdown(report)

    assert "## Simulation Experiments" in markdown
    assert "drift-test (v0.1.0)" in markdown
    assert "Population extinct at generation:** 7" in markdown
    assert "Final mean mutations from reference:** 3.50" in markdown
    assert "a test note" in markdown
