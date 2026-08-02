"""
VirusPlugin base class.

Blueprint Ch.16.3: every plugin supplies reference genomes, gene annotations, protein
annotations, functional domains, and metadata — and nothing else. Plugins provide *data*,
not arbitrary logic that reaches back into engine internals (Ch.16 design constraint,
Ch.5.10 constraint: "Plugins shall provide data rather than arbitrary executable logic
whenever feasible"). This base class enforces that shape.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from viralai.plugins.manifest import PluginManifest


class VirusPlugin(ABC):
    """Base class for all virus plugins. Subclasses supply biology; they never subclass
    or monkeypatch engine behavior.
    """

    manifest: PluginManifest

    @abstractmethod
    def get_reference_genome(self) -> str:
        """Return the validated reference nucleotide sequence for this virus."""

    @abstractmethod
    def get_gene_annotations(self) -> list[dict[str, Any]]:
        """Return gene coordinate annotations, e.g.
        [{"gene": "E6", "start": 104, "end": 559, "strand": "+"}, ...]
        Every entry must be traceable to a citation in
        `manifest.reference_genome_citations` — do not add coordinates the plugin can't
        source.
        """

    @abstractmethod
    def get_protein_annotations(self) -> list[dict[str, Any]]:
        """Return protein-level metadata (domains, known functional motifs) keyed by gene.
        Same sourcing rule as gene annotations: cite it or leave it out.
        """

    def validate(self) -> list[str]:
        """Run plugin-level self-checks and return a list of problems (empty = passes).

        Default implementation checks the basic manifest/data-shape invariants; virus
        plugins can extend this with virus-specific checks but should call
        `super().validate()` first.
        """
        problems: list[str] = []

        genome = self.get_reference_genome()
        if not genome:
            problems.append("get_reference_genome() returned an empty sequence")

        genes = self.get_gene_annotations()
        if not genes:
            problems.append("get_gene_annotations() returned no annotations")
        else:
            for gene in genes:
                for field in ("gene", "start", "end"):
                    if field not in gene:
                        problems.append(f"gene annotation missing required field '{field}': {gene}")
                if "start" in gene and "end" in gene and gene["start"] >= gene["end"]:
                    problems.append(f"gene annotation has start >= end: {gene}")
                if "end" in gene and genome and gene["end"] > len(genome):
                    problems.append(
                        f"gene annotation '{gene.get('gene')}' end={gene['end']} exceeds "
                        f"reference genome length {len(genome)}"
                    )

        if not self.manifest.reference_genome_citations:
            problems.append(
                "manifest declares no reference_genome_citations — required before this "
                "plugin can be certified above EXPERIMENTAL"
            )

        return problems
