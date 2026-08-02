import pytest

from fastapi.testclient import TestClient


@pytest.mark.usefixtures("client")
def test_genomic_search_returns_source_metadata(client: TestClient, monkeypatch):
    async def fake_ncbi_get_json(url: str, params: dict[str, str]):
        if "esearch" in url:
            return {"esearchresult": {"idlist": ["12345"]}}
        if "esummary" in url:
            return {"result": {"uids": ["12345"], "12345": {"accessionversion": "NC_000123", "title": "Test genome", "organism": "Test virus", "slen": 1000}}}
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("viralai.api.routers.genomic._ncbi_get_json", fake_ncbi_get_json)

    response = client.get("/genomic/search?term=hpv")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["source"] == "NCBI"
    assert "ncbi.nlm.nih.gov" in payload[0]["source_url"]
