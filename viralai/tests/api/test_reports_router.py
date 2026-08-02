def _sample_report() -> dict:
    return {
        "title": "API Test Report",
        "provenance": {"software_version": "0.1.0", "virus": "TestVirus"},
        "mutations": [
            {
                "position": 4,
                "reference_base": "A",
                "observed_base": "T",
                "mutation_type": "substitution",
                "confidence_score": 0.9,
            }
        ],
    }


def test_export_markdown(client):
    response = client.post("/reports/export", json=_sample_report(), params={"format": "markdown"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# API Test Report" in response.text


def test_export_json(client):
    response = client.post("/reports/export", json=_sample_report(), params={"format": "json"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_export_csv(client):
    response = client.post("/reports/export", json=_sample_report(), params={"format": "csv"})

    assert response.status_code == 200
    assert "position" in response.text


def test_export_html(client):
    response = client.post("/reports/export", json=_sample_report(), params={"format": "html"})

    assert response.status_code == 200
    assert response.text.startswith("<!DOCTYPE html>")


def test_export_default_format_is_markdown(client):
    response = client.post("/reports/export", json=_sample_report())
    assert "# API Test Report" in response.text


def test_export_unknown_format_returns_400(client):
    response = client.post("/reports/export", json=_sample_report(), params={"format": "pdf"})
    assert response.status_code == 400
