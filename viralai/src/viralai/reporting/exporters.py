"""
Report exporters (Blueprint Ch.19.5).

Implements Markdown, JSON, CSV, and HTML now -- all achievable with the standard library
plus dependencies already in the project. PDF and Excel export are documented, deferred
extensions (see ADR-009): they need new dependencies (reportlab/weasyprint, openpyxl)
that add real weight for formats Markdown/JSON/CSV already cover the substance of.

Every export unconditionally includes the research-use disclaimer (Ch.36) -- see
AnalysisReport.is_research_use_disclaimer_required's docstring for why this is applied
unconditionally rather than computed exactly.
"""

from __future__ import annotations

import csv
import html
import io
import json

from viralai.reporting.report_models import AnalysisReport

RESEARCH_USE_DISCLAIMER = (
    "This report contains computational predictions and/or simulated data. All AI "
    "predictions and simulation results are research-use computational assessments, "
    "not clinical or diagnostic findings, and simulated data does not represent "
    "observed biological evidence."
)


def to_markdown(report: AnalysisReport) -> str:
    lines: list[str] = [f"# {report.title}", ""]

    lines += ["## Provenance", ""]
    lines.append(f"- **Virus:** {report.provenance.virus}")
    lines.append(f"- **Software version:** {report.provenance.software_version}")
    if report.provenance.plugin_name:
        lines.append(
            f"- **Plugin:** {report.provenance.plugin_name} v{report.provenance.plugin_version}"
        )
    if report.provenance.reference_genome_accession:
        lines.append(f"- **Reference genome:** {report.provenance.reference_genome_accession}")
    lines.append(f"- **Generated:** {report.provenance.generated_at.isoformat()}")
    lines.append("")

    if report.mutations:
        lines += ["## Mutations", ""]
        lines.append(
            "| Position | Change | Type | Confidence | Protein Effect | AI Hotspot | Citations |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for m in report.mutations:
            change = f"{m.reference_base}{m.position}{m.observed_base}"
            protein_effect = m.protein_classification or "-"
            ai_flag = (
                "Yes"
                if m.ai_flagged_as_hotspot
                else ("No" if m.ai_flagged_as_hotspot is False else "-")
            )
            citations = f"{len(m.literature_citations)}" if m.literature_citations else "0"
            lines.append(
                f"| {m.position} | {change} | {m.mutation_type} | {m.confidence_score:.2f} | "
                f"{protein_effect} | {ai_flag} | {citations} |"
            )
        lines.append("")

    if report.evolution:
        ev = report.evolution
        lines += ["## Evolutionary Analysis", ""]
        lines.append(f"- **Population size:** {ev.population_size}")
        lines.append(f"- **Nucleotide diversity (π):** {ev.nucleotide_diversity:.4f}")
        lines.append(f"- **Mean entropy:** {ev.mean_entropy:.4f}")
        lines.append(
            f"- **Hotspot positions:** {', '.join(map(str, ev.hotspot_positions)) or 'none'}"
        )
        lines.append("")

    if report.simulations:
        lines += ["## Simulation Experiments", ""]
        for sim in report.simulations:
            lines.append(f"### {sim.experiment_name} (v{sim.experiment_version})")
            lines.append(f"- **Synthetic data:** {sim.is_synthetic}")
            lines.append(f"- **Generations run:** {sim.generations_run}")
            if sim.extinction_generation is not None:
                lines.append(f"- **Population extinct at generation:** {sim.extinction_generation}")
            if sim.final_mean_mutations_from_reference is not None:
                lines.append(
                    "- **Final mean mutations from reference:** "
                    f"{sim.final_mean_mutations_from_reference:.2f}"
                )
            if sim.notes:
                lines.append(f"- **Notes:** {sim.notes}")
            lines.append("")

    if report.summary_notes:
        lines += ["## Summary", "", report.summary_notes, ""]

    lines += ["---", "", f"> {RESEARCH_USE_DISCLAIMER}", ""]
    return "\n".join(lines)


def to_json(report: AnalysisReport) -> str:
    payload = report.model_dump(mode="json")
    payload["research_use_disclaimer"] = RESEARCH_USE_DISCLAIMER
    return json.dumps(payload, indent=2)


def to_csv(report: AnalysisReport) -> str:
    """Mutation table only -- CSV is a tabular format and the mutation list is the only
    naturally tabular section of the report. Evolution/simulation summaries don't have a
    sensible single-table shape, so they're intentionally omitted here (use Markdown/JSON
    for those sections).
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "position",
            "reference_base",
            "observed_base",
            "mutation_type",
            "confidence_score",
            "protein_classification",
            "affected_protein",
            "ai_flagged_as_hotspot",
            "ai_confidence",
            "citation_count",
        ]
    )
    for m in report.mutations:
        writer.writerow(
            [
                m.position,
                m.reference_base,
                m.observed_base,
                m.mutation_type,
                m.confidence_score,
                m.protein_classification or "",
                m.affected_protein or "",
                m.ai_flagged_as_hotspot if m.ai_flagged_as_hotspot is not None else "",
                m.ai_confidence if m.ai_confidence is not None else "",
                len(m.literature_citations),
            ]
        )
    return buffer.getvalue()


def to_html(report: AnalysisReport) -> str:
    """A minimal, dependency-free HTML export -- built directly from the report object,
    not by converting the Markdown output, so each exporter stays independently correct
    rather than one being a lossy transform of another.
    """
    rows = "\n".join(
        f"<tr><td>{m.position}</td><td>{_html(m.reference_base)}&gt;{_html(m.observed_base)}</td>"
        f"<td>{_html(m.mutation_type)}</td><td>{m.confidence_score:.2f}</td>"
        f"<td>{_html(m.protein_classification or '-')}</td>"
        f"<td>{'Yes' if m.ai_flagged_as_hotspot else ('No' if m.ai_flagged_as_hotspot is False else '-')}</td></tr>"
        for m in report.mutations
    )
    mutations_table = (
        "<h2>Mutations</h2><table border='1'><tr><th>Position</th><th>Change</th>"
        "<th>Type</th><th>Confidence</th><th>Protein Effect</th><th>AI Hotspot</th></tr>"
        f"{rows}</table>"
        if report.mutations
        else ""
    )

    evolution_html = ""
    if report.evolution:
        ev = report.evolution
        evolution_html = (
            "<h2>Evolutionary Analysis</h2><ul>"
            f"<li>Population size: {ev.population_size}</li>"
            f"<li>Nucleotide diversity: {ev.nucleotide_diversity:.4f}</li>"
            f"<li>Mean entropy: {ev.mean_entropy:.4f}</li></ul>"
        )

    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{_html(report.title)}</title></head>"
        f"<body><h1>{_html(report.title)}</h1>"
        f"<p><em>Virus: {_html(report.provenance.virus)} | Generated: "
        f"{report.provenance.generated_at.isoformat()}</em></p>"
        f"{mutations_table}{evolution_html}"
        f"<hr/><p><small>{RESEARCH_USE_DISCLAIMER}</small></p>"
        f"</body></html>"
    )


def _html(value: object) -> str:
    """Escape report values before inserting them into an HTML document."""
    return html.escape(str(value), quote=True)
