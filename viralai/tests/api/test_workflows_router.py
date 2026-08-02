import pytest

from fastapi.testclient import TestClient


@pytest.mark.usefixtures("client")
def test_workflow_template_metadata(client: TestClient):
    response = client.get("/workflows/templates/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item["template"] == "mutation_analysis" for item in payload)
    assert any(item["template"] == "simulation" for item in payload)


@pytest.mark.usefixtures("client")
def test_template_run_request_validation(client: TestClient):
    response = client.post(
        "/workflows/templates/run",
        json={
            "template": "mutation_analysis",
            "params": {"reference_genome": "ACGT", "query_genome": "ACGT"},
        },
    )
    assert response.status_code == 422 or response.status_code == 400
    assert "reference_genome and query_genome must differ" in response.text


@pytest.mark.usefixtures("client")
def test_simulation_template_requires_config(client: TestClient):
    response = client.post(
        "/workflows/templates/run",
        json={
            "template": "simulation",
            "params": {
                "reference_genome": "ACGT",
                "name": "sim",
                "version": "v1",
            },
        },
    )
    assert response.status_code == 422 or response.status_code == 400
    assert "Simulation template requires a config object" in response.text


@pytest.mark.usefixtures("client")
def test_workspace_comparison_upload_kicks_off_queued_job(client: TestClient, researcher_api_key: str):
    create_response = client.post(
        "/workspaces",
        json={"title": "Comparison Project"},
        headers={"X-API-Key": researcher_api_key},
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["project_id"]

    response = client.post(
        f"/workspaces/{project_id}/comparisons",
        data={"reference_genome": "ACGTACGT"},
        files={"file": ("sample.fasta", ">sample\nACGTACGT", "text/plain")},
        headers={"X-API-Key": researcher_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["project_id"] == project_id
    assert payload["analysis_name"] == "uploaded-comparison"


@pytest.mark.usefixtures("client")
def test_workspace_comparison_status_endpoint_reports_job_state(client: TestClient, researcher_api_key: str):
    create_response = client.post(
        "/workspaces",
        json={"title": "Status Project"},
        headers={"X-API-Key": researcher_api_key},
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["project_id"]

    create_response = client.post(
        f"/workspaces/{project_id}/comparisons",
        data={"reference_genome": "ACGTACGT"},
        files={"file": ("sample.fasta", ">sample\nACGTACGT", "text/plain")},
        headers={"X-API-Key": researcher_api_key},
    )
    assert create_response.status_code == 200
    payload = create_response.json()

    status_response = client.get(
        f"/workspaces/{project_id}/comparisons/{payload['analysis_name']}",
        headers={"X-API-Key": researcher_api_key},
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["project_id"] == project_id
    assert status_payload["analysis_name"] == payload["analysis_name"]
    assert status_payload["status"] in {"queued", "running", "completed", "failed"}
