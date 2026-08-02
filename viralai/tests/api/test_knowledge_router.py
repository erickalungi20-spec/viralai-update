def _reference(reference_id: str = "ref-1") -> dict:
    return {"reference_id": reference_id, "citation": "Fixture et al. 2024, J Virol"}


def _mutation_knowledge(**overrides) -> dict:
    entry = {
        "virus": "HPV16",
        "gene": "E6",
        "position": 118,
        "reference_base": "C",
        "observed_base": "T",
        "known_effect_summary": "Test effect",
        "evidence_level": "II",
        "reference_ids": ["ref-1"],
    }
    entry.update(overrides)
    return entry


def _auth(key: str) -> dict:
    return {"X-API-Key": key}


def test_add_reference_requires_auth(client):
    response = client.post("/knowledge/references", json=_reference())
    assert response.status_code == 401


def test_add_reference_with_viewer_key_is_forbidden(client, viewer_api_key):
    response = client.post(
        "/knowledge/references", json=_reference(), headers=_auth(viewer_api_key)
    )
    assert response.status_code == 403


def test_add_reference(client, researcher_api_key):
    response = client.post(
        "/knowledge/references", json=_reference(), headers=_auth(researcher_api_key)
    )
    assert response.status_code == 201
    assert response.json()["reference_id"] == "ref-1"


def test_add_duplicate_reference_returns_409(client, researcher_api_key):
    client.post("/knowledge/references", json=_reference(), headers=_auth(researcher_api_key))
    response = client.post(
        "/knowledge/references", json=_reference(), headers=_auth(researcher_api_key)
    )
    assert response.status_code == 409


def test_add_mutation_knowledge_requires_existing_reference(client, researcher_api_key):
    response = client.post(
        "/knowledge/mutations", json=_mutation_knowledge(), headers=_auth(researcher_api_key)
    )
    assert response.status_code == 400  # ref-1 not added yet


def test_add_and_query_mutation_knowledge(client, researcher_api_key):
    client.post("/knowledge/references", json=_reference(), headers=_auth(researcher_api_key))
    add_response = client.post(
        "/knowledge/mutations", json=_mutation_knowledge(), headers=_auth(researcher_api_key)
    )
    assert add_response.status_code == 201

    # reads remain open, no auth needed
    query_response = client.get("/knowledge/mutations", params={"virus": "HPV16", "gene": "E6"})
    assert query_response.status_code == 200
    results = query_response.json()
    assert len(results) == 1
    assert results[0]["position"] == 118


def test_query_mutation_knowledge_with_no_matches_returns_empty(client):
    response = client.get("/knowledge/mutations", params={"virus": "NoSuchVirus"})
    assert response.status_code == 200
    assert response.json() == []


def test_invalid_api_key_is_rejected(client):
    response = client.post(
        "/knowledge/references", json=_reference(), headers=_auth("not-a-real-key")
    )
    assert response.status_code == 401
