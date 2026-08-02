import pytest

from viralai.core.event_bus import EventBus, EventBusError


def test_publish_calls_subscribed_handler():
    bus = EventBus()
    received = []
    bus.subscribe("mutation.detected", lambda event: received.append(event.payload))

    bus.publish("mutation.detected", {"position": 42})

    assert received == [{"position": 42}]


def test_publish_with_no_subscribers_does_not_raise():
    bus = EventBus()
    event = bus.publish("nobody.listening", {"x": 1})
    assert event.topic == "nobody.listening"


def test_multiple_handlers_called_in_registration_order():
    bus = EventBus()
    order = []
    bus.subscribe("topic", lambda e: order.append("first"))
    bus.subscribe("topic", lambda e: order.append("second"))

    bus.publish("topic", {})

    assert order == ["first", "second"]


def test_handler_exception_is_wrapped_and_raised():
    bus = EventBus()

    def bad_handler(event):
        raise ValueError("boom")

    bus.subscribe("topic", bad_handler)

    with pytest.raises(EventBusError):
        bus.publish("topic", {})


def test_history_filters_by_topic():
    bus = EventBus()
    bus.publish("a", {})
    bus.publish("b", {})
    bus.publish("a", {})

    assert len(bus.history("a")) == 2
    assert len(bus.history()) == 3
