"""
Phase 6 Visualization Engine: plot-ready data preparation (plot_data.py, no rendering
dependency) plus static publication-quality PNG rendering via matplotlib (figures.py).
"""

from viralai.visualization.figures import (
    plot_diversity_trend,
    plot_feature_importance,
    plot_genome_map,
)
from viralai.visualization.plot_data import (
    DiversityTrendData,
    FeatureImportanceData,
    GenomeMapData,
    diversity_trend_from_generation_summaries,
    feature_importance_from_dict,
    genome_map_from_mutations,
)

__all__ = [
    "GenomeMapData",
    "DiversityTrendData",
    "FeatureImportanceData",
    "genome_map_from_mutations",
    "diversity_trend_from_generation_summaries",
    "feature_importance_from_dict",
    "plot_genome_map",
    "plot_diversity_trend",
    "plot_feature_importance",
]
