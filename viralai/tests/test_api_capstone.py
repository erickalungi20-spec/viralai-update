"""
Phase 8/9 API capstone: exercises all six API categories (Analysis, Plugin, Knowledge
Base, AI, Simulation, Reporting) PLUS Phase 9's security wiring (auth, Responsible AI
envelopes) through the SDK against a real, live server -- the same kind of end-to-end
proof the seven-phase capstone test (test_full_pipeline_integration.py) gives for the
underlying engines, but for the HTTP surface that wraps them.
"""

from __future__ import annotations

import os

import numpy as np

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.registry import ModelRegistry
from viralai.knowledge.models import LiteratureReference, MutationKnowledge
from viralai.sdk.client import ViralAIClient

REFERENCE_GENOME = "ATGCAATAA"  # M-Q-stop, the fixture gene used across every prior phase
QUERY_GENOME = "ATGCTATAA"  # single missense substitution at position 4
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


def test_api_capstone_all_six_categories_end_to_end(live_server_url, live_server_researcher_key):
    with ViralAIClient(live_server_url, api_key=live_server_researcher_key) as client:
        # -- Analysis API (open, no auth needed) --
        mutations = client.detect_mutations(REFERENCE_GENOME, QUERY_GENOME)
        assert len(mutations) == 1

        protein_mutations = client.analyze_proteins(REFERENCE_GENOME, mutations, GENE_ANNOTATIONS)
        assert protein_mutations[0].classification.value == "missense"

        # -- Plugin API (open) --
        assert client.list_plugins() == []

        # -- Knowledge Base API (writes require RESEARCHER role, which our key has) --
        client.add_reference(
            LiteratureReference(reference_id="ref-1", citation="Fixture et al. 2024")
        )
        client.add_mutation_knowledge(
            MutationKnowledge(
                virus="TestVirus",
                gene="TESTGENE",
                position=4,
                reference_base="A",
                observed_base="T",
                known_effect_summary="Test missense effect",
                evidence_level="II",
                reference_ids=["ref-1"],
            )
        )
        knowledge_results = client.query_mutation_knowledge(virus="TestVirus", gene="TESTGENE")
        assert len(knowledge_results) == 1

        # -- AI API: register a model directly (no HTTP training endpoint, by design --
        # see ADR-011), then predict through the API (RESEARCHER-gated, Responsible AI
        # envelope wrapped) --
        models_dir = os.path.join(os.environ["VIRALAI_DATA_DIR"], "models")
        registry = ModelRegistry(storage_dir=models_dir)
        rng = np.random.RandomState(0)
        X_train = rng.rand(50, 12)
        y_train = (X_train[:, 0] > 0.5).astype(int)
        model = MutationHotspotModel()
        metrics = model.train(X_train, y_train)
        registry.register(
            model,
            name="capstone-model",
            version="0.1.0",
            training_metrics=metrics,
            training_sample_count=50,
        )

        prediction_envelope = client.predict("capstone-model", "0.1.0", [[0.9] + [0.1] * 11])
        assert "disclosure" in prediction_envelope
        assert "limitations" in prediction_envelope
        prediction = prediction_envelope["result"]
        assert len(prediction["predictions"]) == 1

        # -- Simulation API (RESEARCHER-gated, Responsible AI envelope wrapped;
        # SDK unwraps the envelope and returns a SimulationExperiment directly) --
        experiment = client.run_simulation(
            name="capstone-sim",
            version="0.1.0",
            reference_genome=REFERENCE_GENOME,
            population_size=10,
            generations=3,
            mutation_rate=0.05,
            seed=1,
        )
        assert experiment.is_synthetic is True

        # -- Reporting API: build a report from everything gathered above and export it --
        final_summary = (
            experiment.generation_summaries[-1] if experiment.generation_summaries else None
        )
        report = {
            "title": "API Capstone Report",
            "provenance": {"software_version": "0.1.0", "virus": "TestVirus"},
            "mutations": [
                {
                    "position": mutations[0].position,
                    "reference_base": mutations[0].reference_base,
                    "observed_base": mutations[0].observed_base,
                    "mutation_type": mutations[0].mutation_type.value,
                    "confidence_score": mutations[0].confidence_score,
                    "protein_classification": protein_mutations[0].classification.value,
                    "ai_flagged_as_hotspot": prediction["predictions"][0],
                    "ai_confidence": prediction["confidences"][0],
                    "literature_citations": ["publication:ref-1"],
                }
            ],
            "simulations": [
                {
                    "experiment_name": experiment.name,
                    "experiment_version": experiment.version,
                    "is_synthetic": experiment.is_synthetic,
                    "generations_run": len(experiment.generation_summaries),
                    "extinction_generation": experiment.extinction_generation,
                    "final_mean_mutations_from_reference": (
                        final_summary["mean_mutations_from_reference"] if final_summary else None
                    ),
                }
            ],
        }

        markdown = client.export_report(report, format="markdown")

        assert "# API Capstone Report" in markdown
        assert "missense" in markdown
        assert "research-use" in markdown.lower() or "research use" in markdown.lower()


def test_api_capstone_writes_are_rejected_without_authentication(live_server_url):
    """The other side of the story: a client with no API key can read everything but
    cannot write anything, proving the auth gate is real and not just present on paper.
    """
    import httpx
    import pytest

    with ViralAIClient(live_server_url) as anonymous_client:
        # reads still work
        assert anonymous_client.list_plugins() == []

        # writes don't
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            anonymous_client.add_reference(
                LiteratureReference(reference_id="ref-x", citation="Test")
            )
        assert excinfo.value.response.status_code == 401
