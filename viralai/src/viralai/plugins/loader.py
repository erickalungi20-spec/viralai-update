"""
Plugin discovery and loading.

Phase 0 shipped a minimal PluginManager that could register an already-constructed
in-memory object. This module is Phase 1's actual delivery: scan a directory of plugin
packages, load and validate each `manifest.json`, check compatibility against the running
Core Engine version, import the plugin's implementation, run its self-validation, and only
then hand it to the (still Phase-0-provided) registry.

Kept as a separate module rather than rewriting core/plugin_manager.py, so Phase 0's
protocol-based registration (used by tests and the "hello world" proof) keeps working
unmodified — this module is additive.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from viralai import __version__ as CORE_ENGINE_VERSION
from viralai.common.errors import PluginError
from viralai.common.logging import get_logger
from viralai.plugins.base import VirusPlugin
from viralai.plugins.manifest import PluginManifest

logger = get_logger("plugins.loader")

MANIFEST_FILENAME = "manifest.json"


@dataclass
class DiscoveredPlugin:
    manifest: PluginManifest
    instance: VirusPlugin
    source_path: Path


class PluginLoadError(PluginError):
    """Raised when a plugin directory exists but fails manifest parsing, compatibility
    checking, import, or self-validation.
    """


def discover_plugins(plugins_dir: Path | str) -> list[DiscoveredPlugin]:
    """Scan `plugins_dir` for immediate subdirectories containing a manifest.json, load
    and validate each one. A single bad plugin logs an error and is skipped rather than
    aborting discovery for every other plugin — one broken plugin should not take down
    the whole platform.
    """
    base = Path(plugins_dir)
    if not base.exists():
        raise PluginLoadError(f"Plugins directory does not exist: {base}")

    discovered: list[DiscoveredPlugin] = []
    for candidate in sorted(base.iterdir()):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / MANIFEST_FILENAME
        if not manifest_path.exists():
            continue
        try:
            discovered.append(_load_one(candidate, manifest_path))
        except Exception as exc:  # noqa: BLE001 - logged and skipped, not fatal to discovery
            logger.error("skipping plugin at %s: %s", candidate, exc)
    return discovered


def _load_one(plugin_dir: Path, manifest_path: Path) -> DiscoveredPlugin:
    manifest = _load_manifest(manifest_path)

    if not manifest.is_compatible_with(CORE_ENGINE_VERSION):
        raise PluginLoadError(
            f"Plugin '{manifest.name}' v{manifest.version} declares compatibility "
            f"'{manifest.compatible_core_engine_versions}', which does not match the "
            f"running Core Engine version {CORE_ENGINE_VERSION}"
        )

    instance = _import_plugin_instance(plugin_dir, manifest)

    problems = instance.validate()
    if problems:
        raise PluginLoadError(
            f"Plugin '{manifest.name}' failed self-validation:\n  - " + "\n  - ".join(problems)
        )

    logger.info(
        "plugin loaded: %s v%s (%s, tier=%s)",
        manifest.name,
        manifest.version,
        ", ".join(manifest.supported_viruses),
        manifest.certification_tier.value,
    )
    return DiscoveredPlugin(manifest=manifest, instance=instance, source_path=plugin_dir)


def list_plugin_manifests(plugins_dir: Path | str) -> list[PluginManifest]:
    """Scan `plugins_dir` and return every valid manifest.json found, WITHOUT importing
    or validating the plugin's code or reference genome.

    This exists for read-only listing use cases (e.g. the API layer's `GET /plugins`)
    that should work even for plugins whose reference genome hasn't been locally
    provisioned yet (see plugins/hpv16/data/reference/README.md) -- `discover_plugins`
    intentionally requires full validation and would skip such a plugin entirely, which
    is correct for actually *using* a plugin but too strict for just listing what exists.
    """
    base = Path(plugins_dir)
    if not base.exists():
        return []

    manifests: list[PluginManifest] = []
    for candidate in sorted(base.iterdir()):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / MANIFEST_FILENAME
        if not manifest_path.exists():
            continue
        try:
            manifests.append(_load_manifest(manifest_path))
        except Exception as exc:  # noqa: BLE001 -- listing skips bad manifests, doesn't abort
            logger.error("skipping unreadable manifest at %s: %s", manifest_path, exc)
    return manifests


def _load_manifest(manifest_path: Path) -> PluginManifest:
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginLoadError(f"Malformed JSON in {manifest_path}: {exc}") from exc
    try:
        return PluginManifest(**raw)
    except Exception as exc:  # pydantic ValidationError, kept broad-then-wrapped on purpose
        raise PluginLoadError(f"Invalid manifest at {manifest_path}: {exc}") from exc


def _import_plugin_instance(plugin_dir: Path, manifest: PluginManifest) -> VirusPlugin:
    """Import `<plugin_dir>/__init__.py` as a module and instantiate its `Plugin` class.

    This is the one place plugin code gets imported dynamically — every plugin package
    must expose a top-level class literally named `Plugin` implementing VirusPlugin. That
    convention is deliberately rigid so loading stays predictable and auditable.
    """
    init_file = plugin_dir / "__init__.py"
    if not init_file.exists():
        raise PluginLoadError(f"Plugin '{manifest.name}' has no __init__.py at {plugin_dir}")

    module_name = f"viralai_plugin_{manifest.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, init_file)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"Could not build an import spec for {init_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    plugin_class = getattr(module, "Plugin", None)
    if plugin_class is None:
        raise PluginLoadError(
            f"Plugin '{manifest.name}' __init__.py does not define a top-level 'Plugin' class"
        )

    instance = plugin_class(manifest=manifest, plugin_dir=plugin_dir)
    if not isinstance(instance, VirusPlugin):
        raise PluginLoadError(
            f"Plugin '{manifest.name}'s Plugin class does not subclass VirusPlugin"
        )
    return instance
