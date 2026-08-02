import json
import os
from pathlib import Path


def _write_manifest(plugin_dir: Path, **overrides) -> None:
    manifest = {
        "name": plugin_dir.name,
        "version": "0.1.0",
        "supported_viruses": ["FixtureVirus"],
        "compatible_core_engine_versions": "*",
        "authors": ["Test"],
        "license": "Apache-2.0",
        "reference_genome_citations": ["Fixture Citation 2024"],
    }
    manifest.update(overrides)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))


def test_list_plugins_empty_when_no_plugins_dir(client):
    response = client.get("/plugins")
    assert response.status_code == 200
    assert response.json() == []


def test_list_and_get_plugin(client):
    plugins_dir = Path(os.environ["VIRALAI_PLUGINS_DIR"])
    _write_manifest(plugins_dir / "fixture-plugin")

    list_response = client.get("/plugins")
    assert list_response.status_code == 200
    names = [p["name"] for p in list_response.json()]
    assert "fixture-plugin" in names

    get_response = client.get("/plugins/fixture-plugin")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "fixture-plugin"


def test_get_unknown_plugin_returns_404(client):
    response = client.get("/plugins/nonexistent")
    assert response.status_code == 404
