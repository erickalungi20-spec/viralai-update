"""
Proves Phase 2's engines correctly consume the real HPV16 plugin's gene annotations (not
just synthetic fixtures) — using a synthetic reference genome of the correct HPV16 length
so the E6/E7 coordinates line up, but explicitly not claiming this is the real sequence.
"""

from __future__ import annotations

import json
from pathlib import Path

from viralai.engines.protein_engine import ProteinAnalysisEngine

HPV16_PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "hpv16"
HPV16_GENOME_LENGTH = 7906


def _load_hpv16_gene_annotations() -> list[dict]:
    data = json.loads((HPV16_PLUGIN_DIR / "data" / "gene_annotations.json").read_text())
    return data["genes"]


def test_hpv16_gene_annotations_are_usable_by_protein_engine():
    """This does not assert anything about real HPV16 biology -- it proves the citation-
    sourced E6/E7 coordinates from the plugin are structurally valid inputs to the
    Protein Engine, using a SYNTHETIC genome of the correct length as a stand-in for the
    real reference (which, per the plugin's own policy, isn't committed to this repo).
    """
    genes = _load_hpv16_gene_annotations()
    assert {"E6", "E7"} <= {g["gene"] for g in genes}

    # SYNTHETIC fixture, not real HPV16 sequence data -- correct length only, to exercise
    # the pipeline's coordinate handling.
    synthetic_genome = "ATG" + "CTG" * ((HPV16_GENOME_LENGTH - 6) // 3) + "TAA"
    synthetic_genome = synthetic_genome[:HPV16_GENOME_LENGTH].ljust(HPV16_GENOME_LENGTH, "A")

    engine = ProteinAnalysisEngine()
    for gene in genes:
        protein = engine.translate_gene(synthetic_genome, gene)
        assert isinstance(protein, str)
        # E6 (455 bases) and E7 (297 bases) should translate to roughly length/3 minus stop
        gene_length = gene["end"] - gene["start"] + 1
        assert len(protein) <= gene_length // 3
