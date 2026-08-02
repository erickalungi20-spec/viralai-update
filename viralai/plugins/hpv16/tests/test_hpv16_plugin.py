"""
HPV16 plugin tests.

Deliberately split into two groups:
1. Tests that don't need the real reference FASTA (manifest, annotation structure,
   the "missing reference file fails loudly" behavior) — these always run.
2. A full end-to-end discovery test that uses an explicitly SYNTHETIC fixture sequence
   (not real HPV16 data) of the correct length, to prove the loading/validation pipeline
   works mechanically. This does not assert anything about real HPV16 biology.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from viralai.plugins.loader import discover_plugins
from viralai.plugins.manifest import CertificationTier, PluginManifest
from viralai.plugins.reference import ReferenceGenomeNotFoundError

PLUGIN_DIR = Path(__file__).resolve().parents[1]
EXPECTED_GENOME_LENGTH = 7906


def _load_manifest() -> PluginManifest:
    raw = json.loads((PLUGIN_DIR / "manifest.json").read_text())
    return PluginManifest(**raw)


def test_manifest_is_valid_and_experimental():
    manifest = _load_manifest()
    assert manifest.name == "hpv16"
    assert "HPV16" in manifest.supported_viruses
    assert manifest.certification_tier == CertificationTier.EXPERIMENTAL


def test_manifest_declares_citations_for_its_reference_genome():
    manifest = _load_manifest()
    assert manifest.reference_genome_accession == "NC_001526.4"
    assert len(manifest.reference_genome_citations) > 0


def test_gene_annotations_have_citations_and_valid_coordinates():
    data = json.loads((PLUGIN_DIR / "data" / "gene_annotations.json").read_text())
    genes = data["genes"]
    assert len(genes) >= 2  # E6, E7 at minimum

    names = {g["gene"] for g in genes}
    assert {"E6", "E7"} <= names

    for gene in genes:
        assert gene["start"] < gene["end"]
        assert gene["end"] <= EXPECTED_GENOME_LENGTH
        assert gene["citation"], f"gene {gene['gene']} has no citation"


def test_protein_annotations_without_sourced_domains_are_marked_todo_not_fabricated():
    data = json.loads((PLUGIN_DIR / "data" / "protein_annotations.json").read_text())
    for protein in data["proteins"]:
        # This plugin intentionally has not sourced domain boundaries yet -- assert that
        # stays honestly empty rather than someone quietly filling it with unsourced guesses.
        assert protein["functional_domains"] == []


def test_reference_genome_missing_fails_loudly():
    """In this repository, plugins/hpv16/data/reference/reference.fasta is not committed.
    Loading the reference genome must fail with a clear, actionable error, not silently
    substitute placeholder data.
    """
    from viralai.plugins.loader import _import_plugin_instance

    manifest = _load_manifest()
    instance = _import_plugin_instance(PLUGIN_DIR, manifest)

    reference_file = PLUGIN_DIR / "data" / "reference" / "reference.fasta"
    if reference_file.exists():
        pytest.skip("a reference.fasta is present locally; missing-file behavior not exercised")

    with pytest.raises(ReferenceGenomeNotFoundError):
        instance.get_reference_genome()


def test_full_discovery_pipeline_with_synthetic_fixture(tmp_path):
    """End-to-end: copy the real plugin package, drop in a SYNTHETIC (not real HPV16)
    sequence of the correct length, and confirm discover_plugins loads and validates it.
    """
    staged = tmp_path / "plugins"
    staged.mkdir()
    plugin_copy = staged / "hpv16"
    shutil.copytree(PLUGIN_DIR, plugin_copy, ignore=shutil.ignore_patterns("tests", "__pycache__"))

    reference_dir = plugin_copy / "data" / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    synthetic_sequence = (
        "ACGT" * (EXPECTED_GENOME_LENGTH // 4) + "AC"
    )  # length 7906, NOT real HPV16
    assert len(synthetic_sequence) == EXPECTED_GENOME_LENGTH
    (reference_dir / "reference.fasta").write_text(
        ">SYNTHETIC_TEST_FIXTURE not-a-real-HPV16-sequence\n" + synthetic_sequence + "\n"
    )

    discovered = discover_plugins(staged)

    assert len(discovered) == 1
    plugin = discovered[0]
    assert plugin.manifest.name == "hpv16"
    assert len(plugin.instance.get_reference_genome()) == EXPECTED_GENOME_LENGTH
    assert len(plugin.instance.get_gene_annotations()) >= 2
