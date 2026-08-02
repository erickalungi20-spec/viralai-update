import os
from pathlib import Path

import numpy as np

from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.ai.registry import ModelRegistry


def _register_test_model(name: str = "hotspot-test", version: str = "0.1.0") -> None:
    """Registers a model directly into the same storage directory the API's
    lru_cache'd ModelRegistry dependency points at (VIRALAI_DATA_DIR/models) -- there
    is no HTTP training endpoint by design (Phase 4's training pipeline is a deliberate,
    tracked operation, not something the API triggers as a side effect).
    """
    data_dir = Path(os.environ["VIRALAI_DATA_DIR"])
    registry = ModelRegistry(storage_dir=data_dir / "models")

    rng = np.random.RandomState(0)
    X = rng.rand(50, 12)
    y = (X[:, 0] > 0.5).astype(int)
    model = MutationHotspotModel()
    metrics = model.train(X, y)

    registry.register(
        model, name=name, version=version, training_metrics=metrics, training_sample_count=50
    )


def _auth(key: str) -> dict:
    return {"X-API-Key": key}


def test_list_model_versions_empty_when_none_registered(client):
    response = client.get("/ai/models/nonexistent/versions")
    assert response.status_code == 200
    assert response.json() == []


def test_get_model_record(client):
    _register_test_model()
    response = client.get("/ai/models/hotspot-test/0.1.0")
    assert response.status_code == 200
    assert response.json()["name"] == "hotspot-test"


def test_get_unregistered_model_record_returns_404(client):
    response = client.get("/ai/models/nonexistent/0.1.0")
    assert response.status_code == 404


def test_predict_requires_auth(client):
    _register_test_model()
    response = client.post(
        "/ai/models/hotspot-test/0.1.0/predict", json={"feature_vectors": [[0.1] * 12]}
    )
    assert response.status_code == 401


def test_predict(client, researcher_api_key):
    _register_test_model()

    response = client.post(
        "/ai/models/hotspot-test/0.1.0/predict",
        json={"feature_vectors": [[0.9] + [0.1] * 11, [0.1] * 12]},
        headers=_auth(researcher_api_key),
    )

    assert response.status_code == 200
    body = response.json()
    # response is wrapped in a ResponsibleAIEnvelope -- the disclosure is structurally
    # part of the payload, not just accompanying text
    assert "disclosure" in body
    assert "limitations" in body
    result = body["result"]
    assert len(result["predictions"]) == 2
    assert len(result["confidences"]) == 2
    assert all(0.0 <= c <= 1.0 for c in result["confidences"])


def test_predict_with_unregistered_model_returns_404(client, researcher_api_key):
    response = client.post(
        "/ai/models/nonexistent/0.1.0/predict",
        json={"feature_vectors": [[0.1] * 12]},
        headers=_auth(researcher_api_key),
    )
    assert response.status_code == 404


def test_explain_returns_top_features(client, researcher_api_key):
    _register_test_model()

    response = client.post(
        "/ai/models/hotspot-test/0.1.0/explain",
        json={"feature_vector": [0.9] + [0.1] * 11},
        headers=_auth(researcher_api_key),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["feature_names"]
    assert len(body["top_features"]) == 3


def test_reasoning_returns_structured_recommendation(client, researcher_api_key):
    _register_test_model()

    response = client.post(
        "/ai/models/hotspot-test/0.1.0/reason",
        json={
            "virus": "HPV16",
            "mutation": {
                "position": 3,
                "reference_base": "G",
                "observed_base": "A",
                "mutation_type": "substitution",
                "confidence_score": 0.9,
            },
            "reference_genome": "ACGTACGTACGT",
            "gene_annotations": [{"gene": "E6", "start": 1, "end": 12}],
            "genome_length": 12,
            "entropy_at_position": 0.2,
            "population_frequency": 0.05,
        },
        headers=_auth(researcher_api_key),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["virus"] == "HPV16"
    assert body["mutation_summary"]
    assert "recommendation" in body
    assert isinstance(body["top_contributing_features"], list)


def test_register_training_dataset_requires_admin(client, researcher_api_key):
    dataset_payload = {
        "name": "viral-dataset",
        "version": "1.0.0",
        "description": "Test dataset for training",
        "training_examples": [
            {
                "mutation": {
                    "position": 10,
                    "reference_base": "A",
                    "observed_base": "T",
                    "mutation_type": "substitution",
                    "confidence_score": 0.9,
                },
                "context": {
                    "genome_length": 100,
                    "entropy_at_position": 0.2,
                    "population_frequency": 0.1,
                },
                "label": 1,
            }
        ],
        "validation_examples": [],
        "validation_split": 0.0,
    }

    response = client.post(
        "/ai/datasets",
        json=dataset_payload,
        headers={"X-API-Key": researcher_api_key},
    )

    assert response.status_code == 403


def test_register_and_list_training_dataset(client, admin_api_key):
    dataset_payload = {
        "name": "viral-dataset",
        "version": "1.0.0",
        "description": "Test dataset for training",
        "training_examples": [
            {
                "mutation": {
                    "position": 10,
                    "reference_base": "A",
                    "observed_base": "T",
                    "mutation_type": "substitution",
                    "confidence_score": 0.9,
                },
                "context": {
                    "genome_length": 100,
                    "entropy_at_position": 0.2,
                    "population_frequency": 0.1,
                },
                "label": 1,
            }
        ],
        "validation_examples": [],
        "validation_split": 0.0,
    }

    response = client.post(
        "/ai/datasets",
        json=dataset_payload,
        headers={"X-API-Key": admin_api_key},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "viral-dataset"
    assert body["version"] == "1.0.0"
    assert body["training_example_count"] == 1
    assert body["validation_example_count"] == 0

    list_response = client.get("/ai/datasets")
    assert list_response.status_code == 200
    assert any(item["name"] == "viral-dataset" and item["version"] == "1.0.0" for item in list_response.json())

    get_response = client.get("/ai/datasets/viral-dataset/1.0.0")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "viral-dataset"


def test_train_model_from_dataset(client, admin_api_key):
    dataset_payload = {
        "name": "viral-dataset",
        "version": "1.0.0",
        "description": "Test dataset for training",
        "training_examples": [
            {
                "mutation": {
                    "position": 10,
                    "reference_base": "A",
                    "observed_base": "T",
                    "mutation_type": "substitution",
                    "confidence_score": 0.9,
                },
                "context": {
                    "genome_length": 100,
                    "entropy_at_position": 0.2,
                    "population_frequency": 0.1,
                },
                "label": 1,
            }
        ],
        "validation_examples": [],
        "validation_split": 0.0,
    }

    register_response = client.post(
        "/ai/datasets",
        json=dataset_payload,
        headers={"X-API-Key": admin_api_key},
    )
    assert register_response.status_code == 201

    train_payload = {
        "model_name": "dataset-trained-model",
        "model_version": "0.1.0",
        "notes": "Trained from registered dataset",
        "use_validation": False,
    }

    train_response = client.post(
        "/ai/datasets/viral-dataset/1.0.0/train",
        json=train_payload,
        headers={"X-API-Key": admin_api_key},
    )

    assert train_response.status_code == 201
    body = train_response.json()
    assert body["model_record"]["name"] == "dataset-trained-model"
    assert body["model_record"]["version"] == "0.1.0"
    assert body["training_metrics"]
    assert body["feature_importances"]

    versions_response = client.get("/ai/models/dataset-trained-model/versions")
    assert versions_response.status_code == 200
    assert "0.1.0" in versions_response.json()
