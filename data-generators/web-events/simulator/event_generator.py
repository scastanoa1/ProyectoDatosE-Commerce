"""Build the common event envelope described by estructura-evento.md."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from config.settings import EVENT_TARGETS, EVENT_VERSION


class EventGenerator:
    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:16]}"

    @classmethod
    def new_event_id(cls) -> str:
        return cls._new_id("evt")

    @classmethod
    def new_session_id(cls) -> str:
        return cls._new_id("ses")

    @classmethod
    def new_anonymous_id(cls) -> str:
        return cls._new_id("anon")

    @classmethod
    def new_cart_id(cls) -> str:
        return cls._new_id("cart")

    @classmethod
    def new_order_id(cls) -> str:
        return cls._new_id("ord")

    @staticmethod
    def iso_utc(value: datetime | None = None) -> str:
        value = value or datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        # Millisecond precision + Z, matching the documented example format.
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @classmethod
    def build(
        cls,
        *,
        event_type: str,
        customer: dict,
        session_id: str,
        device: dict,
        source: dict,
        payload: dict,
        event_time: datetime | None = None,
    ) -> dict:
        if event_type not in EVENT_TARGETS:
            raise ValueError(f"Unsupported event_type: {event_type}")

        return {
            "event_id": cls.new_event_id(),
            "event_type": event_type,
            "event_version": EVENT_VERSION,
            "event_time": cls.iso_utc(event_time),
            "processing": {"targets": list(EVENT_TARGETS[event_type])},
            "customer": {
                "customer_id": customer.get("customer_id"),
                "anonymous_id": customer.get("anonymous_id"),
            },
            "session": {"session_id": session_id},
            "device": {
                "device_type": device["device_type"],
                "os": device["os"],
                "browser": device["browser"],
            },
            "source": {
                "channel": source["channel"],
                "page": source["page"],
                "referrer": source["referrer"],
            },
            "payload": payload,
        }
