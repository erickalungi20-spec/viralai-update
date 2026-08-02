"""
Phase 5 Simulation Engine + Digital Laboratory Manager.

Mutation Simulator (Jukes-Cantor), Selection Simulator (Wright-Fisher), Environmental
Simulator (position-specific selective pressure), and the Population Simulator that
orchestrates them across generations -- wrapped by the Digital Laboratory Manager's
experiment registry (run, replay, compare).

Every simulation output is explicitly marked `is_synthetic=True` (Ch.13.6) -- simulated
data must never be mistaken for observed biological evidence.
"""

from viralai.simulation.environmental_simulator import EnvironmentalPressure
from viralai.simulation.laboratory import DigitalLaboratoryManager, SimulationExperiment
from viralai.simulation.population_simulator import (
    GenerationSummary,
    PopulationSimulator,
    SimulationConfig,
    SimulationResult,
)
from viralai.simulation.selection_simulator import PopulationExtinctError

__all__ = [
    "EnvironmentalPressure",
    "PopulationSimulator",
    "SimulationConfig",
    "SimulationResult",
    "GenerationSummary",
    "PopulationExtinctError",
    "DigitalLaboratoryManager",
    "SimulationExperiment",
]
