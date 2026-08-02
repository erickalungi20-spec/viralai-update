import importlib.util


def test_ai_package_discoverable():
    """Quick discovery test: ensure `viralai.ai` can be found without importing heavy deps."""
    spec = importlib.util.find_spec("viralai.ai")
    assert spec is not None, "viralai.ai package not discoverable"
