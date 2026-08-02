"""
Scientific Cache.

Protein translation, entropy calculations, domain lookups, and mutation frequency counts
get recomputed constantly on overlapping inputs across a research session. Rather than
recompute, memoize by content hash.

Phase 0 implementation uses `diskcache` (a local, dependency-free, file-backed cache) so
this works with zero external infrastructure. It sits behind the same call signature a
Redis-backed cache would use, so swapping the backend later doesn't touch call sites —
see docs/adr/ADR-004-phase0-pragmatic-infrastructure.md.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, TypeVar

from diskcache import Cache

from viralai.common.logging import get_logger

logger = get_logger("core.cache")

_CACHE_DIR = Path(os.environ.get("VIRALAI_CACHE_DIR", ".viralai_cache"))
_cache = Cache(str(_CACHE_DIR))

F = TypeVar("F", bound=Callable[..., Any])


def _make_cache_key(func: Callable[..., Any], args: tuple, kwargs: dict) -> str:
    """Build a stable cache key from the function's qualified name and its arguments.

    Arguments must be JSON-serializable (or have a stable repr) — this is intentional:
    scientific cache inputs should be simple, inspectable values (sequences, positions,
    parameters), not opaque objects, so cache behavior stays predictable and debuggable.
    """
    try:
        payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    except TypeError:
        payload = repr((args, kwargs))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{func.__module__}.{func.__qualname__}:{digest}"


def scientific_cache(func: F) -> F:
    """Memoize a pure function's results on disk, keyed by its arguments.

    Only use this on deterministic, side-effect-free functions — that's the contract that
    makes caching safe. Do not decorate anything that reads mutable global state or has
    side effects.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = _make_cache_key(func, args, kwargs)
        if key in _cache:
            logger.debug("cache hit: %s", func.__qualname__)
            return _cache[key]
        logger.debug("cache miss: %s", func.__qualname__)
        result = func(*args, **kwargs)
        _cache[key] = result
        return result

    wrapper.cache_clear = _cache.clear  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]


def clear_cache() -> None:
    """Wipe the entire Scientific Cache. Mainly for tests and benchmark reruns."""
    _cache.clear()
