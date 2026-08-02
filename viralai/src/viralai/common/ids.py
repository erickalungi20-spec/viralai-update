"""ID generation. One function, used everywhere an object needs a UUID."""

from __future__ import annotations

import uuid


def new_id(prefix: str | None = None) -> str:
    """Generate a UUID4-based identifier, optionally namespaced with a prefix.

    Examples:
        new_id() -> "3fae2b1e-6b7a-4e9d-9f2f-6b6a1e9d3fae"
        new_id("mutation") -> "mutation-3fae2b1e-6b7a-4e9d-9f2f-6b6a1e9d3fae"
    """
    raw = str(uuid.uuid4())
    return f"{prefix}-{raw}" if prefix else raw
