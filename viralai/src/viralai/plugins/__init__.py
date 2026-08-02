"""
Phase 1 Plugin System: manifest specification, certification tiers, the VirusPlugin
contract, reference genome validation, and directory-based plugin discovery.
"""

from viralai.plugins.base import VirusPlugin
from viralai.plugins.loader import (
    DiscoveredPlugin,
    PluginLoadError,
    discover_plugins,
    list_plugin_manifests,
)
from viralai.plugins.manifest import CertificationTier, PluginManifest
from viralai.plugins.reference import (
    ReferenceGenomeNotFoundError,
    ReferenceGenomeSpec,
    load_reference_genome,
)

__all__ = [
    "VirusPlugin",
    "PluginManifest",
    "CertificationTier",
    "discover_plugins",
    "list_plugin_manifests",
    "DiscoveredPlugin",
    "PluginLoadError",
    "ReferenceGenomeSpec",
    "ReferenceGenomeNotFoundError",
    "load_reference_genome",
]
