"""
HPV16 plugin implementation.

Certification tier: experimental (see manifest.json). This plugin ships verified E6/E7
gene coordinates with citations; other genes and all protein functional-domain boundaries
are intentionally left as documented TODOs rather than guessed — see
data/protein_annotations.json and docs/PLUGIN_DEVELOPMENT_STANDARD.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from viralai.plugins.base import VirusPlugin
from viralai.plugins.manifest import PluginManifest
from viralai.plugins.reference import ReferenceGenomeSpec, load_reference_genome

EXPECTED_GENOME_LENGTH = 7906  # NC_001526.4 -- see manifest.json citations


class Plugin(VirusPlugin):
    def __init__(self, manifest: PluginManifest, plugin_dir: Path) -> None:
        self.manifest = manifest
        self._plugin_dir = plugin_dir
        self._data_dir = plugin_dir / "data"

    def get_reference_genome(self) -> str:
        spec = ReferenceGenomeSpec(
            accession=self.manifest.reference_genome_accession or "NC_001526.4",
            expected_length=EXPECTED_GENOME_LENGTH,
        )
        fasta_path = self._data_dir / "reference" / "reference.fasta"
        return load_reference_genome(fasta_path, spec)

    def get_gene_annotations(self) -> list[dict[str, Any]]:
        return self._load_json("gene_annotations.json")["genes"]

    def get_protein_annotations(self) -> list[dict[str, Any]]:
        return self._load_json("protein_annotations.json")["proteins"]

    def _load_json(self, filename: str) -> dict[str, Any]:
        return json.loads((self._data_dir / filename).read_text())
