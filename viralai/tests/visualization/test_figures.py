from viralai.visualization.figures import (
    plot_diversity_trend,
    plot_feature_importance,
    plot_genome_map,
)
from viralai.visualization.plot_data import DiversityTrendData, FeatureImportanceData, GenomeMapData


def test_plot_genome_map_creates_a_nonempty_png(tmp_path):
    data = GenomeMapData(
        genome_length=1000,
        positions=[10, 500, 900],
        confidence_scores=[0.9, 0.5, 0.2],
        mutation_types=["substitution", "insertion", "deletion"],
    )
    output_path = tmp_path / "genome_map.png"

    result_path = plot_genome_map(data, output_path)

    assert result_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_genome_map_handles_empty_data(tmp_path):
    data = GenomeMapData(genome_length=100, positions=[], confidence_scores=[], mutation_types=[])
    output_path = tmp_path / "empty_map.png"

    plot_genome_map(data, output_path)

    assert output_path.exists()


def test_plot_diversity_trend_creates_a_nonempty_png(tmp_path):
    data = DiversityTrendData(
        generations=[0, 1, 2],
        nucleotide_diversity=[0.0, 0.02, 0.05],
        mean_mutations_from_reference=[0.0, 0.5, 1.2],
    )
    output_path = tmp_path / "diversity.png"

    plot_diversity_trend(data, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_feature_importance_creates_a_nonempty_png(tmp_path):
    data = FeatureImportanceData(feature_names=["a", "b", "c"], values=[0.5, -0.3, 0.1])
    output_path = tmp_path / "importance.png"

    plot_feature_importance(data, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_output_directory_is_created_if_missing(tmp_path):
    data = GenomeMapData(
        genome_length=100, positions=[10], confidence_scores=[0.9], mutation_types=["substitution"]
    )
    nested_path = tmp_path / "nested" / "dir" / "map.png"

    plot_genome_map(data, nested_path)

    assert nested_path.exists()
