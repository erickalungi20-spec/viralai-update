import pytest
from pydantic import ValidationError as PydanticValidationError

from viralai.plugins.manifest import CertificationTier, PluginManifest


def _base_manifest_kwargs(**overrides):
    kwargs = dict(
        name="test-plugin",
        version="0.1.0",
        supported_viruses=["TestVirus"],
        compatible_core_engine_versions=">=0.1.0",
        authors=["Someone"],
        license="Apache-2.0",
    )
    kwargs.update(overrides)
    return kwargs


def test_manifest_defaults_to_experimental_tier():
    manifest = PluginManifest(**_base_manifest_kwargs())
    assert manifest.certification_tier == CertificationTier.EXPERIMENTAL


def test_manifest_requires_at_least_one_supported_virus():
    with pytest.raises(PydanticValidationError):
        PluginManifest(**_base_manifest_kwargs(supported_viruses=[]))


def test_manifest_requires_at_least_one_author():
    with pytest.raises(PydanticValidationError):
        PluginManifest(**_base_manifest_kwargs(authors=[]))


@pytest.mark.parametrize(
    "spec,core_version,expected",
    [
        (">=0.1.0", "0.1.0", True),
        (">=0.1.0", "0.2.0", True),
        (">=0.2.0", "0.1.0", False),
        ("==0.1.0", "0.1.0", True),
        ("==0.1.0", "0.2.0", False),
        ("*", "9.9.9", True),
    ],
)
def test_is_compatible_with(spec, core_version, expected):
    manifest = PluginManifest(**_base_manifest_kwargs(compatible_core_engine_versions=spec))
    assert manifest.is_compatible_with(core_version) is expected
