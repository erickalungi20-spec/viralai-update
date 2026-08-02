"""
httpx's sync Client cannot use ASGITransport (that's async-only), and the SDK
deliberately uses a sync client for simplicity in normal use. So SDK tests run against
a real, live uvicorn server on a background thread rather than an in-process transport
shortcut -- this is slightly more setup, but it means the SDK tests exercise an actual
HTTP round trip, which is what the SDK is actually for.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn

from viralai.api.dependencies import reset_cached_dependencies


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server_url(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRALAI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VIRALAI_PLUGINS_DIR", str(tmp_path / "plugins"))
    reset_cached_dependencies()

    from viralai.api.app import app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(f"{base_url}/health", timeout=1.0)
            break
        except httpx.ConnectError:
            time.sleep(0.05)
    else:
        raise RuntimeError("live test server did not start in time")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5.0)
    reset_cached_dependencies()


@pytest.fixture
def live_server_researcher_key(live_server_url):
    """Issues a RESEARCHER-role API key directly against the same APIKeyStore file the
    live server's VIRALAI_DATA_DIR points at (bypassing HTTP, same bootstrap pattern as
    the CLI's `issue-api-key` command), for tests that need to exercise
    auth-gated endpoints (knowledge writes, AI predictions, simulation runs).
    """
    from viralai.api.auth import get_api_key_store
    from viralai.security.roles import Role

    store = get_api_key_store()
    raw_key, _ = store.issue_key("test-live-researcher", Role.RESEARCHER)
    return raw_key
