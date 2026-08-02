"""
Roles (Blueprint Ch.35.3 Authorization).

Three roles, ordered by privilege. Kept deliberately small -- a research platform's real
access-control needs (who can write curated knowledge, who can run compute-costly
simulations, who administers API keys) map cleanly onto three tiers without needing a
general-purpose permissions system yet.
"""

from __future__ import annotations

from enum import IntEnum


class Role(IntEnum):
    """IntEnum so roles compare naturally: Role.VIEWER < Role.RESEARCHER < Role.ADMIN."""

    VIEWER = 1
    RESEARCHER = 2
    ADMIN = 3
