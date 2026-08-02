def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_endpoint(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_openapi_schema_is_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "ViralAI API"
    # every router category should show up as a tagged path
    paths = " ".join(schema["paths"].keys())
    for expected in ("/analysis", "/plugins", "/knowledge", "/ai", "/simulation", "/reports"):
        assert expected in paths


def test_homepage_serves_ui_shell(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "ViralAI Research Studio" in response.text
