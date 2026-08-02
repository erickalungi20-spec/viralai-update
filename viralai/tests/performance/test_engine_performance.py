"""
Performance tests (Blueprint Ch.32.3): assert timing/throughput bounds, distinct from
correctness tests elsewhere. Bounds here are set generously (an order of magnitude above
observed local performance) specifically to avoid flakiness on slower CI runners --
these exist to catch a real performance regression (e.g. an accidentally-quadratic
change), not to enforce a tight SLA.
"""

from __future__ import annotations

import time

import numpy as np

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.engines.mutation_engine import MutationEngine
from viralai.simulation.population_simulator import PopulationSimulator, SimulationConfig


def test_mutation_detection_completes_quickly_for_gene_length_sequence():
    engine = MutationEngine()
    reference = "ACGT" * 250  # 1000bp, gene-length scale
    query = "ACGA" * 250

    start = time.perf_counter()
    engine.detect_mutations(reference, query)
    elapsed = time.perf_counter() - start

    assert (
        elapsed < 2.0
    ), f"Mutation detection took {elapsed:.2f}s, expected well under 2s for 1000bp"


def test_alignment_based_detection_completes_within_bound_for_gene_length_indel():
    """The O(n*m) alignment path from ADR-005 -- specifically bounded because this is
    the known scaling-limited path, not the equal-length fast path.
    """
    engine = MutationEngine()
    reference = "ACGT" * 250  # 1000bp
    query = "ACGT" * 249 + "ACG"  # 997bp, one base short

    start = time.perf_counter()
    engine.detect_mutations(reference, query)
    elapsed = time.perf_counter() - start

    assert (
        elapsed < 10.0
    ), f"Alignment-based detection took {elapsed:.2f}s, expected under 10s for ~1000bp"


def test_population_simulation_completes_within_bound():
    simulator = PopulationSimulator()
    config = SimulationConfig(population_size=200, generations=50, mutation_rate=0.01, seed=1)
    reference = "ACGT" * 100  # 400bp

    start = time.perf_counter()
    simulator.run(reference, config)
    elapsed = time.perf_counter() - start

    assert elapsed < 15.0, f"Simulation took {elapsed:.2f}s, expected under 15s for this scale"


def test_ai_model_training_completes_within_bound():
    rng = np.random.RandomState(0)
    X = rng.rand(2000, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel(n_estimators=100)

    start = time.perf_counter()
    model.train(X, y)
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0, f"Training took {elapsed:.2f}s, expected under 10s for 2000 samples"


def test_ai_model_prediction_throughput():
    rng = np.random.RandomState(0)
    X_train = rng.rand(200, 12)
    y_train = (X_train[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    model.train(X_train, y_train)

    X_predict = rng.rand(5000, 12)

    start = time.perf_counter()
    model.predict(X_predict)
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0, f"Predicting 5000 rows took {elapsed:.2f}s, expected under 5s"
