import json

from fastapi.testclient import TestClient


from viralai.api.app import app
from viralai.security.api_keys import APIKeyStore
from viralai.api.auth import reset_auth_cache
from viralai.security.roles import Role


client = TestClient(app)


def _issue_test_key():
    store = APIKeyStore(storage_path=".viralai_api_data/api_keys.json")
    raw, record = store.issue_key("test-key", Role.RESEARCHER)
    # Ensure the FastAPI auth dependency reloads the key store next time it's used
    reset_auth_cache()
    return raw


def _fasta_bytes(name: str, seq: str) -> tuple[str, tuple[str, bytes, str]]:
    return (
        name,
        (f"{name}.fasta", f">{name}\n{seq}\n".encode("utf-8"), "text/plain"),
    )


def test_evaluate_single_query():
    # reference and one query
    files = [
        ("reference", ("ref.fasta", ">ref\nACGTACGT\n", "text/plain")),
        ("queries", ("q1.fasta", ">q1\nACGTAGGT\n", "text/plain")),
    ]

    key = _issue_test_key()
    resp = client.post("/analysis/evaluate", files=files, headers={"X-API-Key": key})
    assert resp.status_code == 200
    body = resp.json()
    assert "reports" in body
    assert len(body["reports"]) == 1
    r = body["reports"][0]
    assert r["mutation_count"] == 1


def test_evaluate_multiple_queries():
    files = [
        ("reference", ("ref.fasta", ">ref\nACGTACGT\n", "text/plain")),
        ("queries", ("q1.fasta", ">q1\nACGTAGGT\n", "text/plain")),
        ("queries", ("q2.fasta", ">q2\nACGTCGT\n", "text/plain")),
    ]

    key = _issue_test_key()
    resp = client.post("/analysis/evaluate", files=files, headers={"X-API-Key": key})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["reports"]) == 2
