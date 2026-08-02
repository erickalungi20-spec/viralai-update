"""
Static figure rendering (Blueprint Ch.28 "publication-quality figures").

Uses matplotlib's non-interactive Agg backend -- this is a backend library with no
display, so figures are always rendered headless to files. Interactive dashboards
(Ch.28.6, VR exploration, real-time streaming) are explicitly out of scope here: those
need an actual UI to be interactive in, which doesn't exist until Phase 8's API layer at
the earliest. See ADR-009.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless rendering, must happen before pyplot import

from pathlib import Path  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

from viralai.visualization.plot_data import DiversityTrendData, FeatureImportanceData, GenomeMapData

_MUTATION_TYPE_COLORS = {
    "substitution": "#4C72B0",
    "insertion": "#55A868",
    "deletion": "#C44E52",
}


def plot_genome_map(
    data: GenomeMapData, output_path: Path | str, *, title: str = "Genome Mutation Map"
) -> Path:
    """One point per mutation along the genome, colored by mutation type, positioned by
    confidence. Saved as PNG.
    """
    fig, ax = plt.subplots(figsize=(10, 3))

    for mutation_type in set(data.mutation_types):
        xs = [p for p, t in zip(data.positions, data.mutation_types) if t == mutation_type]
        ys = [c for c, t in zip(data.confidence_scores, data.mutation_types) if t == mutation_type]
        ax.scatter(
            xs,
            ys,
            label=mutation_type,
            color=_MUTATION_TYPE_COLORS.get(mutation_type, "#888888"),
            s=40,
        )

    ax.set_xlim(0, data.genome_length)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Genome position")
    ax.set_ylabel("Confidence score")
    ax.set_title(title)
    if data.mutation_types:
        ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_diversity_trend(
    data: DiversityTrendData,
    output_path: Path | str,
    *,
    title: str = "Population Diversity Over Generations",
) -> Path:
    """Nucleotide diversity and mean mutation count per generation from a simulation --
    always labeled as synthetic data in the title, per Ch.13.6.
    """
    fig, ax1 = plt.subplots(figsize=(8, 4))

    ax1.plot(
        data.generations,
        data.nucleotide_diversity,
        color="#4C72B0",
        label="Nucleotide diversity (pi)",
    )
    ax1.set_xlabel("Generation")
    ax1.set_ylabel("Nucleotide diversity (pi)", color="#4C72B0")
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    ax2 = ax1.twinx()
    ax2.plot(
        data.generations,
        data.mean_mutations_from_reference,
        color="#C44E52",
        label="Mean mutations from reference",
    )
    ax2.set_ylabel("Mean mutations from reference", color="#C44E52")
    ax2.tick_params(axis="y", labelcolor="#C44E52")

    ax1.set_title(f"{title} [SYNTHETIC DATA]")
    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_feature_importance(
    data: FeatureImportanceData, output_path: Path | str, *, title: str = "Feature Contribution"
) -> Path:
    """Horizontal bar chart of feature importances/SHAP values -- the AI Dashboard's
    explainability chart (Ch.28.3).
    """
    fig, ax = plt.subplots(figsize=(7, max(2, 0.4 * len(data.feature_names))))

    order = sorted(range(len(data.values)), key=lambda i: abs(data.values[i]))
    names_sorted = [data.feature_names[i] for i in order]
    values_sorted = [data.values[i] for i in order]
    colors = ["#C44E52" if v < 0 else "#4C72B0" for v in values_sorted]

    ax.barh(names_sorted, values_sorted, color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Contribution")
    ax.set_title(title)
    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
