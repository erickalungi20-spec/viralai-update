import json
from pathlib import Path

from viralai.plugins.loader import discover_plugins, list_plugin_manifests


def _write_manifest(plugin_dir: Path, **overrides) -> None:
    manifest = {
        "name": plugin_dir.name,
        "version": "0.1.0",
        "supported_viruses": ["FixtureVirus"],
        "compatible_core_engine_versions": "*",
        "authors": ["Test"],
        "license": "Apache-2.0",
        "reference_genome_citations": ["Fixture Citation 2024"],
    }
    manifest.update(overrides)
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))


def _write_plugin_impl(plugin_dir: Path, genome: str = "ACGT" * 10) -> None:
    (plugin_dir / "__init__.py").write_text(f"""
from typing import Any
from pathlib import Path
from viralai.plugins.base import VirusPlugin
from viralai.plugins.manifest import PluginManifest


class Plugin(VirusPlugin):
    def __init__(self, manifest: PluginManifest, plugin_dir: Path) -> None:
        self.manifest = manifest

    def get_reference_genome(self) -> str:
        return {genome!r}

    def get_gene_annotations(self) -> list:
        return [{{"gene": "X", "start": 0, "end": 10}}]

    def get_protein_annotations(self) -> list:
        return []
""")


def test_discover_plugins_finds_and_loads_a_well_formed_plugin(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_dir = plugins_dir / "fixture-plugin"
    plugin_dir.mkdir()
    _write_manifest(plugin_dir)
    _write_plugin_impl(plugin_dir)

    discovered = discover_plugins(plugins_dir)

    assert len(discovered) == 1
    assert discovered[0].manifest.name == "fixture-plugin"
    assert discovered[0].instance.get_reference_genome() == "ACGT" * 10


def test_discover_plugins_skips_directory_without_manifest(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "not-a-plugin").mkdir()

    discovered = discover_plugins(plugins_dir)

    assert discovered == []


def test_discover_plugins_skips_incompatible_core_engine_version(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_dir = plugins_dir / "incompatible-plugin"
    plugin_dir.mkdir()
    _write_manifest(plugin_dir, compatible_core_engine_versions=">=99.0.0")
    _write_plugin_impl(plugin_dir)

    discovered = discover_plugins(plugins_dir)

    assert discovered == []  # skipped, not raised -- one bad plugin shouldn't abort discovery


def test_discover_plugins_skips_plugin_failing_self_validation(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_dir = plugins_dir / "empty-genome-plugin"
    plugin_dir.mkdir()
    _write_manifest(plugin_dir)
    _write_plugin_impl(plugin_dir, genome="")  # empty genome fails VirusPlugin.validate()

    discovered = discover_plugins(plugins_dir)

    assert discovered == []


def test_discover_plugins_skips_malformed_json_manifest(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_dir = plugins_dir / "broken-manifest-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text("{not valid json")
    _write_plugin_impl(plugin_dir)

    discovered = discover_plugins(plugins_dir)

    assert discovered == []


def test_multiple_plugins_one_broken_does_not_block_the_others(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    good_dir = plugins_dir / "good-plugin"
    good_dir.mkdir()
    _write_manifest(good_dir)
    _write_plugin_impl(good_dir)

    bad_dir = plugins_dir / "bad-plugin"
    bad_dir.mkdir()
    _write_manifest(bad_dir)
    _write_plugin_impl(bad_dir, genome="")

    discovered = discover_plugins(plugins_dir)

    assert len(discovered) == 1
    assert discovered[0].manifest.name == "good-plugin"


class TestListPluginManifests:
    """list_plugin_manifests() is deliberately lighter than discover_plugins(): it
    should succeed for a plugin whose code/reference genome isn't set up yet, since it
    never imports or validates anything -- it just reads manifest.json files.
    """

    def test_lists_manifest_without_importing_or_validating(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        plugin_dir = plugins_dir / "unimportable-plugin"
        plugin_dir.mkdir()
        _write_manifest(plugin_dir)
        # deliberately no __init__.py and no reference genome -- discover_plugins would
        # fail on this, list_plugin_manifests should not care

        manifests = list_plugin_manifests(plugins_dir)

        assert len(manifests) == 1
        assert manifests[0].name == "unimportable-plugin"

    def test_returns_empty_list_for_missing_directory(self, tmp_path):
        assert list_plugin_manifests(tmp_path / "does-not-exist") == []

    def test_skips_malformed_manifest_without_raising(self, tmp_path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        broken_dir = plugins_dir / "broken"
        broken_dir.mkdir()
        (broken_dir / "manifest.json").write_text("{not valid json")

        assert list_plugin_manifests(plugins_dir) == []

    def test_finds_the_real_hpv16_plugin_manifest(self):
        """Sanity check against the actual repository plugin, not just fixtures."""
        real_plugins_dir = Path(__file__).resolve().parents[2] / "plugins"
        manifests = list_plugin_manifests(real_plugins_dir)
        names = {m.name for m in manifests}
        assert "hpv16" in names
