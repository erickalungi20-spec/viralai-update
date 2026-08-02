import pytest
from fastapi.testclient import TestClient

from viralai.api.dependencies import reset_cached_dependencies


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient wired to isolated, per-test storage directories -- each test gets
    its own Knowledge Base / Model Registry / Simulation Lab on disk, and the
    lru_cache'd dependency getters are cleared before and after so tests never leak
    state into each other.
    """
    monkeypatch.setenv("VIRALAI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VIRALAI_PLUGINS_DIR", str(tmp_path / "plugins"))
    reset_cached_dependencies()

    from viralai.api.app import app

    with TestClient(app) as test_client:
        yield test_client

    reset_cached_dependencies()


@pytest.fixture
def researcher_api_key(client):
    """Issues a RESEARCHER-role key directly against the store (bypassing HTTP, since
    issuing keys itself requires ADMIN -- see admin_api_key for how the first key gets
    minted) and returns the raw key string for use in an X-API-Key header.
    """
    from viralai.api.auth import get_api_key_store
    from viralai.security.roles import Role

    store = get_api_key_store()
    raw_key, _ = store.issue_key("test-researcher", Role.RESEARCHER)
    return raw_key


@pytest.fixture
def admin_api_key(client):
    from viralai.api.auth import get_api_key_store
    from viralai.security.roles import Role

    store = get_api_key_store()
    raw_key, _ = store.issue_key("test-admin", Role.ADMIN)
    return raw_key


@pytest.fixture
def viewer_api_key(client):
    from viralai.api.auth import get_api_key_store
    from viralai.security.roles import Role

    store = get_api_key_store()
    raw_key, _ = store.issue_key("test-viewer", Role.VIEWER)
    return raw_key
