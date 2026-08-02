"""
API dependency injection.

Every underlying registry (Knowledge Base, Model Registry, Digital Laboratory Manager)
is file-backed and needs a storage root. This module is the one place that decides where
those roots live, driven by environment variables with sensible local defaults, and
exposes them as FastAPI dependencies so route handlers never construct these objects
directly -- that's what makes `dependency_overrides` in tests work cleanly.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from viralai.ai.dataset_repository import DatasetRepository
from viralai.ai.registry import ModelRegistry
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.knowledge.store import KnowledgeBase
from viralai.security.audit import AuditLogger
from viralai.simulation.laboratory import DigitalLaboratoryManager
from viralai.core.engine import CoreEngine
from viralai.workflow.checkpoint import CheckpointManager
from viralai.storage.sqlite_adapter import SQLiteModelRegistry
from viralai.ai.dataset_repository import DatasetRepository


def _data_root() -> Path:
    return Path(os.environ.get("VIRALAI_DATA_DIR", ".viralai_api_data"))


def _plugins_root() -> Path:
    return Path(os.environ.get("VIRALAI_PLUGINS_DIR", "plugins"))


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(persist_path=_data_root() / "knowledge_base")


@lru_cache
def get_model_registry() -> ModelRegistry:
    # Allow selecting a DB-backed registry via env var for stronger persistence.
    backend = os.environ.get("VIRALAI_MODEL_REGISTRY", "file")
    if backend == "sqlite":
        return SQLiteModelRegistry(_data_root() / "models")
    return ModelRegistry(storage_dir=_data_root() / "models")


@lru_cache
def get_dataset_repository() -> DatasetRepository:
    return DatasetRepository(storage_dir=_data_root() / "datasets")


@lru_cache
def get_benchmark_repository() -> BenchmarkRepository:
    return BenchmarkRepository(_data_root() / "benchmark_history.json")


@lru_cache
def get_simulation_lab() -> DigitalLaboratoryManager:
    return DigitalLaboratoryManager(storage_dir=_data_root() / "simulations")


@lru_cache
def get_audit_logger() -> AuditLogger:
    return AuditLogger(storage_path=_data_root() / "audit_log.jsonl")


def get_plugins_dir() -> Path:
    return _plugins_root()


def get_data_root() -> Path:
    return _data_root()


def get_workspaces_dir() -> Path:
    """Return the API-owned root for persistent research workspaces.

    The workspace module intentionally accepts any project directory so it can be used
    directly by scripts. The API narrows that freedom to a single directory below the
    configured data root, preventing a request from choosing arbitrary filesystem paths.
    """
    return _data_root() / "workspaces"


@lru_cache
def get_core_engine() -> CoreEngine:
    return CoreEngine()


@lru_cache
def get_checkpoint_manager() -> CheckpointManager:
    return CheckpointManager(storage_dir=_data_root() / "checkpoints")


def reset_cached_dependencies() -> None:
    """Clear the lru_cache on every dependency getter -- tests call this between cases
    that use different VIRALAI_DATA_DIR/VIRALAI_PLUGINS_DIR values, since lru_cache
    would otherwise silently keep serving the first test's instances.
    """
    get_knowledge_base.cache_clear()
    get_model_registry.cache_clear()
    get_dataset_repository.cache_clear()
    get_benchmark_repository.cache_clear()
    get_simulation_lab.cache_clear()
    get_audit_logger.cache_clear()

    from viralai.api.auth import reset_auth_cache

    reset_auth_cache()
