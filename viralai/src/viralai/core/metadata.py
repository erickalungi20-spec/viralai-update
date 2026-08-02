"""
Unified Metadata Engine.

Every object ViralAI produces (a Mutation, a Protein, a Simulation, an AI prediction, a
Report) must carry: a UUID, who/what created it, a timestamp, plugin version, workflow
version, software version, evidence level, and confidence score (Ch.29, Reviewer
Recommendation 5). Rather than trust every engine to remember to set these fields by hand,
this module wraps any object once, at creation time.

Design choice: metadata is attached as an *envelope* around a payload object rather than
mixed into the payload's own fields. This keeps the IDM models (idm.py) clean and
independent of the metadata concern, and means metadata handling can change without
touching every model in idm.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from viralai.common.ids import new_id

T = TypeVar("T")

VIRALAI_SOFTWARE_VERSION = "0.1.0"


class Metadata(BaseModel):
    """The provenance envelope fields every tracked object gets, automatically."""

    uuid: str = Field(default_factory=lambda: new_id())
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    software_version: str = VIRALAI_SOFTWARE_VERSION
    plugin_name: str | None = None
    plugin_version: str | None = None
    workflow_version: str | None = None
    evidence_level: str | None = None
    confidence_score: float | None = None


class Tracked(BaseModel, Generic[T]):
    """A payload plus its automatically-generated Metadata envelope.

    Usage:
        mutation = Mutation(...)
        tracked = attach_metadata(mutation, created_by="mutation_engine")
        tracked.metadata.uuid       # auto-generated
        tracked.payload             # the original Mutation, untouched
    """

    payload: T
    metadata: Metadata


def attach_metadata(
    payload: T,
    *,
    created_by: str = "system",
    plugin_name: str | None = None,
    plugin_version: str | None = None,
    workflow_version: str | None = None,
    evidence_level: str | None = None,
    confidence_score: float | None = None,
) -> Tracked[T]:
    """Wrap `payload` in a Metadata envelope. This is the only sanctioned way to attach
    provenance — do not construct Metadata objects ad hoc inside engine code, or the
    "no developer should have to manually add these fields" guarantee breaks down.
    """
    metadata = Metadata(
        created_by=created_by,
        plugin_name=plugin_name,
        plugin_version=plugin_version,
        workflow_version=workflow_version,
        evidence_level=evidence_level,
        confidence_score=confidence_score,
    )
    return Tracked(payload=payload, metadata=metadata)


def metadata_summary(tracked: Tracked[Any]) -> dict[str, Any]:
    """Human-readable provenance summary, suitable for embedding in a report footer."""
    md = tracked.metadata
    return {
        "id": md.uuid,
        "created": md.created_at.isoformat(),
        "created_by": md.created_by,
        "software_version": md.software_version,
        "plugin": f"{md.plugin_name}@{md.plugin_version}" if md.plugin_name else None,
        "workflow_version": md.workflow_version,
        "evidence_level": md.evidence_level,
        "confidence_score": md.confidence_score,
    }
