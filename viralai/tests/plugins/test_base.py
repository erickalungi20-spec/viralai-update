from typing import Any

from viralai.plugins.base import VirusPlugin
from viralai.plugins.manifest import PluginManifest


def _manifest(**overrides) -> PluginManifest:
    kwargs = dict(
        name="fixture-plugin",
        version="0.1.0",
        supported_viruses=["FixtureVirus"],
        compatible_core_engine_versions="*",
        authors=["Test"],
        license="Apache-2.0",
        reference_genome_citations=["Some Citation 2024"],
    )
    kwargs.update(overrides)
    return PluginManifest(**kwargs)


class _MinimalPlugin(VirusPlugin):
    def __init__(self, manifest: PluginManifest, genome: str, genes: list[dict[str, Any]]):
        self.manifest = manifest
        self._genome = genome
        self._genes = genes

    def get_reference_genome(self) -> str:
        return self._genome

    def get_gene_annotations(self) -> list[dict[str, Any]]:
        return self._genes

    def get_protein_annotations(self) -> list[dict[str, Any]]:
        return []


def test_validate_passes_for_well_formed_plugin():
    plugin = _MinimalPlugin(
        manifest=_manifest(),
        genome="ACGT" * 10,
        genes=[{"gene": "X", "start": 0, "end": 10}],
    )
    assert plugin.validate() == []


def test_validate_flags_empty_genome():
    plugin = _MinimalPlugin(
        manifest=_manifest(), genome="", genes=[{"gene": "X", "start": 0, "end": 5}]
    )
    problems = plugin.validate()
    assert any("empty sequence" in p for p in problems)


def test_validate_flags_gene_end_beyond_genome_length():
    plugin = _MinimalPlugin(
        manifest=_manifest(),
        genome="ACGT",  # length 4
        genes=[{"gene": "X", "start": 0, "end": 100}],
    )
    problems = plugin.validate()
    assert any("exceeds reference genome length" in p for p in problems)


def test_validate_flags_start_greater_than_or_equal_end():
    plugin = _MinimalPlugin(
        manifest=_manifest(),
        genome="ACGT" * 10,
        genes=[{"gene": "X", "start": 10, "end": 5}],
    )
    problems = plugin.validate()
    assert any("start >= end" in p for p in problems)


def test_validate_flags_missing_reference_genome_citations():
    plugin = _MinimalPlugin(
        manifest=_manifest(reference_genome_citations=[]),
        genome="ACGT" * 10,
        genes=[{"gene": "X", "start": 0, "end": 10}],
    )
    problems = plugin.validate()
    assert any("reference_genome_citations" in p for p in problems)
