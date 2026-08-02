import pytest

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.registry import ModelRegistry
from viralai.knowledge.models import LiteratureReference, MutationKnowledge
from viralai.sdk.client import ViralAIClient

REFERENCE_GENOME = "ATGCAATAA"
QUERY_GENOME = "ATGCTATAA"
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


@pytest.fixture
def sdk_client(live_server_url, live_server_researcher_key):
    with ViralAIClient(live_server_url, api_key=live_server_researcher_key) as client:
        yield client


def test_sdk_detect_mutations(sdk_client):
    mutations = sdk_client.detect_mutations(REFERENCE_GENOME, QUERY_GENOME)
    assert len(mutations) == 1
    assert mutations[0].position == 4


def test_sdk_analyze_proteins(sdk_client):
    mutations = sdk_client.detect_mutations(REFERENCE_GENOME, QUERY_GENOME)
    protein_mutations = sdk_client.analyze_proteins(REFERENCE_GENOME, mutations, GENE_ANNOTATIONS)
    assert len(protein_mutations) == 1
    assert protein_mutations[0].classification.value == "missense"


def test_sdk_list_plugins_empty(sdk_client):
    assert sdk_client.list_plugins() == []


def test_sdk_knowledge_round_trip(sdk_client):
    reference = LiteratureReference(reference_id="ref-1", citation="Fixture 2024")
    sdk_client.add_reference(reference)

    entry = MutationKnowledge(
        virus="HPV16",
        gene="E6",
        position=118,
        reference_base="C",
        observed_base="T",
        known_effect_summary="Test",
        evidence_level="II",
        reference_ids=["ref-1"],
    )
    sdk_client.add_mutation_knowledge(entry)

    results = sdk_client.query_mutation_knowledge(virus="HPV16", gene="E6")
    assert len(results) == 1
    assert results[0].position == 118


def test_sdk_predict(sdk_client, live_server_url):
    import os

    import numpy as np

    data_dir = os.environ["VIRALAI_DATA_DIR"]
    registry = ModelRegistry(storage_dir=f"{data_dir}/models")
    rng = np.random.RandomState(0)
    X = rng.rand(50, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    metrics = model.train(X, y)
    registry.register(
        model,
        name="sdk-test-model",
        version="0.1.0",
        training_metrics=metrics,
        training_sample_count=50,
    )

    result = sdk_client.predict("sdk-test-model", "0.1.0", [[0.9] + [0.1] * 11])

    assert "disclosure" in result
    assert "limitations" in result
    assert len(result["result"]["predictions"]) == 1


def test_sdk_run_simulation(sdk_client):
    experiment = sdk_client.run_simulation(
        name="sdk-test",
        version="0.1.0",
        reference_genome="ACGTACGTACGTACGTACGT",
        population_size=10,
        generations=3,
        mutation_rate=0.05,
        seed=1,
    )
    assert experiment.is_synthetic is True
    assert experiment.name == "sdk-test"


def test_sdk_export_report(sdk_client):
    report = {
        "title": "SDK Test Report",
        "provenance": {"software_version": "0.1.0", "virus": "TestVirus"},
    }
    markdown = sdk_client.export_report(report, format="markdown")
    assert "# SDK Test Report" in markdown


def test_sdk_context_manager_closes_client(live_server_url):
    with ViralAIClient(live_server_url) as client:
        assert client.list_plugins() == []


def test_sdk_write_without_api_key_raises(live_server_url):
    with ViralAIClient(live_server_url) as client:
        reference = LiteratureReference(reference_id="ref-1", citation="Fixture 2024")
        import httpx

        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            client.add_reference(reference)
        assert excinfo.value.response.status_code == 401
