def _auth(key: str) -> dict:
    return {"X-API-Key": key}


def test_issue_api_key_requires_admin(client, researcher_api_key):
    response = client.post(
        "/admin/api-keys",
        json={"label": "new-key", "role": "researcher"},
        headers=_auth(researcher_api_key),
    )
    assert response.status_code == 403


def test_issue_api_key_as_admin(client, admin_api_key):
    response = client.post(
        "/admin/api-keys",
        json={"label": "new-key", "role": "researcher"},
        headers=_auth(admin_api_key),
    )
    assert response.status_code == 201
    body = response.json()
    assert "raw_key" in body
    assert body["record"]["label"] == "new-key"
    assert body["record"]["role"] == 2  # Role.RESEARCHER


def test_issued_key_actually_works(client, admin_api_key):
    issue_response = client.post(
        "/admin/api-keys",
        json={"label": "usable-key", "role": "researcher"},
        headers=_auth(admin_api_key),
    )
    new_raw_key = issue_response.json()["raw_key"]

    # the freshly issued key should be usable for a RESEARCHER-gated endpoint
    reference_response = client.post(
        "/knowledge/references",
        json={"reference_id": "ref-x", "citation": "Test"},
        headers=_auth(new_raw_key),
    )
    assert reference_response.status_code == 201


def test_list_api_keys_requires_admin(client, researcher_api_key):
    response = client.get("/admin/api-keys", headers=_auth(researcher_api_key))
    assert response.status_code == 403


def test_list_api_keys_as_admin(client, admin_api_key, researcher_api_key):
    response = client.get("/admin/api-keys", headers=_auth(admin_api_key))
    assert response.status_code == 200
    labels = [r["label"] for r in response.json()]
    assert "test-admin" in labels
    assert "test-researcher" in labels
    # raw keys are never exposed in listings
    assert all("raw_key" not in r for r in response.json())


def test_revoke_api_key(client, admin_api_key):
    issue_response = client.post(
        "/admin/api-keys",
        json={"label": "to-revoke", "role": "researcher"},
        headers=_auth(admin_api_key),
    )
    key_id = issue_response.json()["record"]["key_id"]
    raw_key = issue_response.json()["raw_key"]

    revoke_response = client.post(f"/admin/api-keys/{key_id}/revoke", headers=_auth(admin_api_key))
    assert revoke_response.status_code == 204

    # the revoked key should no longer work
    response = client.post(
        "/knowledge/references",
        json={"reference_id": "ref-y", "citation": "Test"},
        headers=_auth(raw_key),
    )
    assert response.status_code == 401


def test_revoke_nonexistent_key_returns_404(client, admin_api_key):
    response = client.post("/admin/api-keys/nonexistent/revoke", headers=_auth(admin_api_key))
    assert response.status_code == 404
