import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(r"c:\Users\PC\Desktop\New folder\viralai-phases-0-to-10\viralai\src").resolve()))

from fastapi.testclient import TestClient
from viralai.api.app import app
from viralai.api.dependencies import reset_cached_dependencies

with tempfile.TemporaryDirectory() as tmp:
    os.environ["VIRALAI_DATA_DIR"] = tmp
    reset_cached_dependencies()
    client = TestClient(app)
    from viralai.api.auth import get_api_key_store
    from viralai.security.roles import Role

    store = get_api_key_store()
    raw, _ = store.issue_key("test-researcher", Role.RESEARCHER)
    payload = {
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
    r1 = client.post("/ai/datasets", json=payload, headers={"X-API-Key": raw})
    print("dataset", r1.status_code, r1.text)
    r2 = client.post(
        "/ai/datasets/viral-dataset/1.0.0/train",
        json={"model_name": "dataset-trained-model", "model_version": "0.1.0", "notes": "x", "use_validation": False},
        headers={"X-API-Key": raw},
    )
    print("train", r2.status_code, r2.text)
