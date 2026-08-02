import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from viralai.api.app import app
from viralai.api.dependencies import reset_cached_dependencies
from viralai.api.auth import get_api_key_store
from viralai.security.roles import Role

root = Path(tempfile.mkdtemp())
os.environ['VIRALAI_DATA_DIR'] = str(root)
os.environ['VIRALAI_PLUGINS_DIR'] = str(root / 'plugins')
reset_cached_dependencies()

store = get_api_key_store()
raw_key, _ = store.issue_key('debug-researcher', Role.RESEARCHER)

with TestClient(app) as client:
    dataset_payload = {
        'name': 'viral-dataset',
        'version': '1.0.0',
        'description': 'Test dataset for training',
        'training_examples': [
            {
                'mutation': {
                    'position': 10,
                    'reference_base': 'A',
                    'observed_base': 'T',
                    'mutation_type': 'substitution',
                    'confidence_score': 0.9,
                },
                'context': {
                    'genome_length': 100,
                    'entropy_at_position': 0.2,
                    'population_frequency': 0.1,
                },
                'label': 1,
            }
        ],
        'validation_examples': [],
        'validation_split': 0.0,
    }

    register_response = client.post('/ai/datasets', json=dataset_payload, headers={'X-API-Key': raw_key})
    print('register', register_response.status_code, register_response.text)

    train_payload = {
        'model_name': 'dataset-trained-model',
        'model_version': '0.1.0',
        'notes': 'Trained from registered dataset',
        'use_validation': False,
    }

    train_response = client.post('/ai/datasets/viral-dataset/1.0.0/train', json=train_payload, headers={'X-API-Key': raw_key})
    print('train', train_response.status_code, train_response.text)
