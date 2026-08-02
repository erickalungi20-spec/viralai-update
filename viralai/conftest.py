"""
Root conftest: auto-applies the Ch.32.3 test pyramid markers (unit / integration /
system / plugin / performance) based on test location, so the pyramid is queryable
(`pytest -m system`, `pytest -m plugin`) without having to hand-annotate all several
hundred existing tests one by one. New tests get classified automatically by where they
live, which is also a forcing function for putting new tests in the right place.

Classification rules, in priority order:
1. Anything under a `<plugin>/tests/` directory -> plugin
2. Anything under `tests/performance/` -> performance
3. `tests/test_full_pipeline_integration.py` and `tests/test_api_capstone.py` (the
   capstone tests that exercise the whole platform end to end) -> system
4. Any other test file with "integration" in its name -> integration
5. Everything else -> unit
"""

from __future__ import annotations


def pytest_collection_modifyitems(config, items):
    import pytest

    for item in items:
        # Pytest exposes native paths; normalize them before applying the
        # repository-layout rules so marker selection behaves the same on Windows,
        # Linux CI, and containers.
        path = str(item.fspath).replace("\\", "/")

        if "/plugins/" in path and "/tests/" in path:
            item.add_marker(pytest.mark.plugin)
        elif "/tests/performance/" in path:
            item.add_marker(pytest.mark.performance)
        elif path.endswith("test_full_pipeline_integration.py") or path.endswith(
            "test_api_capstone.py"
        ):
            item.add_marker(pytest.mark.system)
        elif "integration" in path:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
