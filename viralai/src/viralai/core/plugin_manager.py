"""
Plugin Manager (Phase 0 minimal version).

Phase 0's exit criteria requires that a "hello world" plugin can be loaded and registered
through the Core Engine — this proves the virus-independent/plugin-supplies-biology
boundary actually works end to end. The full system (manifest spec, certification tiers,
signature validation — Blueprint Ch.16, 31) is Phase 1 scope. This is deliberately the
smallest thing that could plausibly be called a plugin system.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from viralai.common.errors import PluginError
from viralai.common.logging import get_logger

logger = get_logger("core.plugin_manager")


@runtime_checkable
class ViralAIPlugin(Protocol):
    """The minimal contract every plugin must satisfy to be loadable.

    Phase 1 will extend this with manifest metadata, certification status, and a
    validation lifecycle. For now: a name, a version, and a supported-virus declaration
    is enough to prove the Core Engine can be virus-independent while a plugin supplies
    virus-specific identity.
    """

    name: str
    version: str
    supported_virus: str


class PluginManager:
    """Registers and looks up plugins by name. No filesystem discovery yet — Phase 1."""

    def __init__(self) -> None:
        self._plugins: dict[str, ViralAIPlugin] = {}

    def register(self, plugin: ViralAIPlugin) -> None:
        if not isinstance(plugin, ViralAIPlugin):
            raise PluginError(
                f"Object of type {type(plugin).__name__} does not satisfy the "
                f"ViralAIPlugin protocol (needs .name, .version, .supported_virus)"
            )
        if plugin.name in self._plugins:
            raise PluginError(f"Plugin '{plugin.name}' is already registered")
        self._plugins[plugin.name] = plugin
        logger.info(
            "plugin registered: %s v%s (%s)", plugin.name, plugin.version, plugin.supported_virus
        )

    def get(self, name: str) -> ViralAIPlugin:
        if name not in self._plugins:
            raise PluginError(f"No plugin registered under name '{name}'")
        return self._plugins[name]

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins.keys())
