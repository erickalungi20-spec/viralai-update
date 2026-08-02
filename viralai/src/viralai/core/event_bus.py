"""
Event Bus.

Engines publish events (e.g. "mutation.detected") rather than calling each other directly,
so the Mutation Engine doesn't need to know the Protein Engine exists, and either can be
swapped, tested alone, or scaled independently later.

Phase 0 implementation: a synchronous, in-process pub/sub bus with no external
infrastructure. This is a deliberate scope decision — see
docs/adr/ADR-004-phase0-pragmatic-infrastructure.md. It implements the same conceptual
interface (publish/subscribe by topic, ordered delivery, at-least-once within a process)
that a Redis Streams-backed bus will implement when distributed execution is actually
needed. Call sites should never depend on this being in-process.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from viralai.common.errors import ViralAIError
from viralai.common.ids import new_id
from viralai.common.logging import get_logger

logger = get_logger("core.event_bus")

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A single message travelling through the bus."""

    topic: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: new_id("evt"))
    emitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None


class EventBusError(ViralAIError):
    """Raised when a subscriber handler fails while processing an event."""


class EventBus:
    """A minimal, synchronous, topic-based publish/subscribe bus.

    Not a singleton by design — tests and future multi-tenant use cases should be able to
    construct isolated buses rather than share global state.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register `handler` to be called whenever an event is published to `topic`."""
        self._subscribers[topic].append(handler)
        logger.debug("subscribed handler to topic=%s", topic)

    def publish(self, topic: str, payload: dict[str, Any], *, source: str | None = None) -> Event:
        """Publish an event to `topic`. Handlers run synchronously, in registration order.

        A handler exception is logged and re-raised as EventBusError rather than silently
        swallowed — a failed handler is a real problem the caller needs to know about,
        not something to hide behind "the event bus decouples everything."
        """
        event = Event(topic=topic, payload=payload, source=source)
        self._history.append(event)
        logger.debug("publishing event id=%s topic=%s source=%s", event.event_id, topic, source)

        for handler in self._subscribers.get(topic, []):
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - intentionally broad, re-raised typed
                logger.exception("handler failed for topic=%s", topic)
                raise EventBusError(
                    f"Subscriber to topic '{topic}' raised {type(exc).__name__}: {exc}"
                ) from exc
        return event

    def history(self, topic: str | None = None) -> list[Event]:
        """Return published events, optionally filtered by topic. Test/debug convenience."""
        if topic is None:
            return list(self._history)
        return [e for e in self._history if e.topic == topic]
