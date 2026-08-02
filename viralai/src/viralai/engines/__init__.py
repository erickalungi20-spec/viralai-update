"""
Phase 2 Core Scientific Engines: Mutation Analysis, Protein Analysis, Evolution Analysis.

These are the first engines that consume plugin-supplied reference genomes and gene
annotations (Phase 1) to produce real scientific output. AI Engine (Phase 4) and
Simulation Engine (Phase 5) build on top of what these three produce.
"""

from viralai.engines.evolution_engine import EvolutionAnalysisEngine
from viralai.engines.mutation_engine import MutationEngine
from viralai.engines.protein_engine import ProteinAnalysisEngine, estimate_substitution_severity

__all__ = [
    "MutationEngine",
    "ProteinAnalysisEngine",
    "estimate_substitution_severity",
    "EvolutionAnalysisEngine",
]
