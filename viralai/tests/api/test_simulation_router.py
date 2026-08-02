REFERENCE_GENOME = "ACGTACGTACGTACGTACGT"


def _run_request(**overrides) -> dict:
    payload = {
        "name": "test-experiment",
        "version": "0.1.0",
        "reference_genome": REFERENCE_GENOME,
        "population_size": 10,
        "generations": 3,
        "mutation_rate": 0.05,
        "seed": 1,
        "notes": "test run",
    }
    payload.update(overrides)
    return payload


def _auth(key: str) -> dict:
    return {"X-API-Key": key}


def test_run_experiment_requires_auth(client):
    response = client.post("/simulation/experiments", json=_run_request())
    assert response.status_code == 401


def test_run_experiment(client, researcher_api_key):
    response = client.post(
        "/simulation/experiments", json=_run_request(), headers=_auth(researcher_api_key)
    )

    assert response.status_code == 201
    body = response.json()
    # response is wrapped in a ResponsibleAIEnvelope
    assert "disclosure" in body
    assert "limitations" in body
    result = body["result"]
    assert result["is_synthetic"] is True
    assert result["name"] == "test-experiment"
    assert len(result["generation_summaries"]) == 3


def test_run_duplicate_experiment_returns_409(client, researcher_api_key):
    client.post("/simulation/experiments", json=_run_request(), headers=_auth(researcher_api_key))
    response = client.post(
        "/simulation/experiments", json=_run_request(), headers=_auth(researcher_api_key)
    )
    assert response.status_code == 409


def test_get_experiment(client, researcher_api_key):
    client.post("/simulation/experiments", json=_run_request(), headers=_auth(researcher_api_key))

    # reads remain open, no auth needed
    response = client.get("/simulation/experiments/test-experiment/0.1.0")

    assert response.status_code == 200
    assert response.json()["notes"] == "test run"


def test_get_unregistered_experiment_returns_404(client):
    response = client.get("/simulation/experiments/nonexistent/0.1.0")
    assert response.status_code == 404


def test_list_experiment_versions(client, researcher_api_key):
    client.post(
        "/simulation/experiments",
        json=_run_request(version="0.1.0"),
        headers=_auth(researcher_api_key),
    )
    client.post(
        "/simulation/experiments",
        json=_run_request(version="0.2.0"),
        headers=_auth(researcher_api_key),
    )

    response = client.get("/simulation/experiments/test-experiment/versions")

    assert set(response.json()) == {"0.1.0", "0.2.0"}
