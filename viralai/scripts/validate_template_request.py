import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath('src'))
from viralai.api.app import app

client = TestClient(app)

for payload in [
    {'template': 'mutation_analysis', 'params': {'reference_genome': 'ACGT', 'query_genome': 'ACGT'}},
    {'template': 'simulation', 'params': {'reference_genome': 'ACGT', 'name': 'sim', 'version': 'v1'}}
]:
    response = client.post('/workflows/templates/run', json=payload)
    print('payload', payload)
    print('status', response.status_code)
    print(response.text)
    print('json', response.json())
    print('---')
