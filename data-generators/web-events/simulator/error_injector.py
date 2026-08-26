"""Controlled data-quality error injection for Sprint 1 profiling/testing."""

from __future__ import annotations

from copy import deepcopy
import random


REQUIRED_PAYLOAD_FIELDS = {
    "page_view": ["page", "page_type"],
    "category_view": ["category_id"],
    "product_view": ["product_id", "category_id"],
    "search": ["query", "results_count"],
    "search_no_results": ["query", "results_count"],
    "product_favorite": ["product_id", "action"],
    "product_share": ["product_id", "platform"],
    "add_to_cart": ["product_id", "quantity", "unit_price", "currency"],
    "remove_from_cart": ["product_id", "quantity"],
    "cart_view": ["cart_id", "items_count", "total_amount", "currency"],
    "checkout_started": ["order_id", "items_count", "total_amount", "currency"],
    "checkout_shipping": ["order_id", "shipping_method", "shipping_cost", "currency"],
    "checkout_payment": ["order_id", "payment_method"],
    "checkout_abandoned": ["order_id", "step", "cart_value", "currency"],
    "purchase": ["order_id", "total_amount", "currency", "items"],
    "payment_success": ["order_id", "payment_method", "amount", "currency"],
    "payment_failed": ["order_id", "payment_method", "amount", "currency", "error_code"],
    "order_cancelled": ["order_id", "reason"],
    "session_started": ["landing_page"],
    "session_ended": [
        "duration_seconds",
        "pages_viewed",
        "products_viewed",
        "items_added_to_cart",
        "purchase_completed",
    ],
    "login": ["login_method", "success", "ip_country", "failure_reason"],
}


class ErrorInjector:
    """Inject at most one controlled error into a selected event."""

    def __init__(self, error_rate: float, rng: random.Random) -> None:
        if not 0.0 <= error_rate <= 1.0:
            raise ValueError("error_rate must be between 0 and 1.")
        self.error_rate = error_rate
        self.rng = rng
        self.previous_event_ids: list[str] = []

    def process(self, event: dict) -> dict:
        candidate = deepcopy(event)

        if self.rng.random() < self.error_rate:
            candidate = self._inject_one(candidate)

        # Keep emitted IDs, including intentionally duplicated IDs, so future duplicate
        # tests can still select from the observed stream.
        if candidate.get("event_id"):
            self.previous_event_ids.append(str(candidate["event_id"]))
        return candidate

    def _inject_one(self, event: dict) -> dict:
        choices = [
            self._null_required_field,
            self._invalid_timestamp,
            self._wrong_type,
            self._invalid_product_id,
            self._category_mismatch,
            self._incomplete_payload,
        ]
        if self.previous_event_ids:
            choices.append(self._duplicate_event_id)

        self.rng.shuffle(choices)
        for injector in choices:
            if injector(event):
                return event

        # Defensive fallback: every event has event_version according to the envelope.
        event["event_version"] = "1"
        return event

    def _duplicate_event_id(self, event: dict) -> bool:
        if not self.previous_event_ids:
            return False
        event["event_id"] = self.rng.choice(self.previous_event_ids)
        return True

    @staticmethod
    def _invalid_timestamp(event: dict) -> bool:
        event["event_time"] = "invalid-timestamp"
        return True

    def _null_required_field(self, event: dict) -> bool:
        # Common-envelope fields are documented as part of every event.
        paths = [
            ("session", "session_id"),
            ("device", "device_type"),
            ("source", "channel"),
        ]
        parent, field = self.rng.choice(paths)
        event[parent][field] = None
        return True

    def _wrong_type(self, event: dict) -> bool:
        numeric_payload_fields = [
            "results_count",
            "quantity",
            "unit_price",
            "items_count",
            "total_amount",
            "shipping_cost",
            "cart_value",
            "amount",
            "duration_seconds",
            "pages_viewed",
            "products_viewed",
            "items_added_to_cart",
        ]
        available = [field for field in numeric_payload_fields if field in event["payload"]]
        if available:
            field = self.rng.choice(available)
            event["payload"][field] = str(event["payload"][field])
            return True

        if event["event_type"] == "login" and "success" in event["payload"]:
            event["payload"]["success"] = str(event["payload"]["success"]).lower()
            return True

        event["event_version"] = "1"
        return True

    @staticmethod
    def _invalid_product_id(event: dict) -> bool:
        if "product_id" in event["payload"]:
            event["payload"]["product_id"] = "prod_DOES_NOT_EXIST"
            return True
        if event["event_type"] == "purchase" and event["payload"].get("items"):
            event["payload"]["items"][0]["product_id"] = "prod_DOES_NOT_EXIST"
            return True
        return False

    @staticmethod
    def _category_mismatch(event: dict) -> bool:
        if event["event_type"] != "product_view":
            return False
        event["payload"]["category_id"] = "cat_999"
        return True

    def _incomplete_payload(self, event: dict) -> bool:
        required = REQUIRED_PAYLOAD_FIELDS.get(event["event_type"], [])
        if not required:
            return False
        field = self.rng.choice(required)
        event["payload"].pop(field, None)
        return True
