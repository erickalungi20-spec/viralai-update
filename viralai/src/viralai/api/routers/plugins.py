"""
Plugin API (Blueprint Ch.30.3 Plugin API): read-only listing of what plugins are
available. Uses `list_plugin_manifests` (not `discover_plugins`) deliberately -- the API
should be able to tell a client "HPV16 plugin exists, tier=experimental" even before
someone has provisioned the real reference genome locally.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from viralai.api.dependencies import get_plugins_dir
from viralai.plugins.loader import list_plugin_manifests
from viralai.plugins.manifest import PluginManifest

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginManifest])
def list_plugins(plugins_dir=Depends(get_plugins_dir)) -> list[PluginManifest]:
    return list_plugin_manifests(plugins_dir)


@router.get("/{name}", response_model=PluginManifest)
def get_plugin(name: str, plugins_dir=Depends(get_plugins_dir)) -> PluginManifest:
    manifests = list_plugin_manifests(plugins_dir)
    for manifest in manifests:
        if manifest.name == name:
            return manifest
    raise HTTPException(status_code=404, detail=f"No plugin named '{name}'")
