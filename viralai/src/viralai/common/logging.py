"""
Logging.

One place that configures how ViralAI logs, so every engine's log output is consistent and
machine-parseable (important later for the Provenance Manager, which needs to correlate log
entries with analysis runs).
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False
_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configure_root_logger(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    root = logging.getLogger("viralai")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger, e.g. get_logger('viralai.core.engine')."""
    _configure_root_logger()
    if not name.startswith("viralai"):
        name = f"viralai.{name}"
    return logging.getLogger(name)
