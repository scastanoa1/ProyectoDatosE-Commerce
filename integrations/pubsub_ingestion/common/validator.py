from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

ALLOWED_TARGETS = {"batch", "streaming"}

PAYLOAD_SCHEMAS: dict[str, dict[str, Any]] = {
    "page_view": {"page": str, "page_type": str},
    "category_view": {"category_id": str},
    "product_view": {"product_id": str, "category_id": str},
    "search": {"query": str, "results_count": int},
    "search_no_results": {"query": str, "results_count": int},
    "product_favorite": {"product_id": str, "action": str},
    "product_share": {"product_id": str, "platform": str},
    "add_to_cart": {
        "product_id": str,
        "quantity": int,
        "unit_price": "number",
        "currency": str,
    },
    "remove_from_cart": {"product_id": str, "quantity": int},
    "cart_view": {
        "cart_id": str,
        "items_count": int,
        "total_amount": "number",
        "currency": str,
    },
    "checkout_started": {
        "order_id": str,
        "items_count": int,
        "total_amount": "number",
        "currency": str,
    },
    "checkout_shipping": {
        "order_id": str,
        "shipping_method": str,
        "shipping_cost": "number",
        "currency": str,
    },
    "checkout_payment": {
        "order_id": str,
        "payment_method": str,
    },
    "checkout_abandoned": {
        "order_id": str,
        "step": str,
        "cart_value": "number",
        "currency": str,
    },
    "purchase": {
        "order_id": str,
        "total_amount": "number",
        "currency": str,
        "items": list,
    },
    "payment_success": {
        "order_id": str,
        "payment_method": str,
        "amount": "number",
        "currency": str,
    },
    "payment_failed": {
        "order_id": str,
        "payment_method": str,
        "amount": "number",
        "currency": str,
        "error_code": str,
    },
    "order_cancelled": {
        "order_id": str,
        "reason": str,
    },
    "session_started": {
        "landing_page": str,
    },
    "session_ended": {
        "duration_seconds": int,
        "pages_viewed": int,
        "products_viewed": int,
        "items_added_to_cart": int,
        "purchase_completed": bool,
    },
    "login": {
        "login_method": str,
        "success": bool,
        "ip_country": str,
        "failure_reason": "nullable_string",
    },
}

# Contrato documentado de routing por event_type.
EXPECTED_TARGETS: dict[str, set[str]] = {
    "page_view": {"batch"},
    "category_view": {"batch"},
    "product_view": {"batch", "streaming"},
    "search": {"batch", "streaming"},
    "search_no_results": {"batch"},
    "product_favorite": {"batch", "streaming"},
    "product_share": {"batch"},
    "add_to_cart": {"batch", "streaming"},
    "remove_from_cart": {"batch", "streaming"},
    "cart_view": {"batch"},
    "checkout_started": {"batch"},
    "checkout_shipping": {"batch"},
    "checkout_payment": {"batch"},
    "checkout_abandoned": {"batch"},
    "purchase": {"batch", "streaming"},
    "payment_success": {"batch", "streaming"},
    "payment_failed": {"batch", "streaming"},
    "order_cancelled": {"batch"},
    "session_started": {"batch"},
    "session_ended": {"batch"},
    "login": {"batch", "streaming"},
}


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]


class EventValidator:
    def validate(self, event: Any) -> ValidationResult:
        errors: list[str] = []

        if not isinstance(event, dict):
            return ValidationResult(False, ["Event root must be a JSON object."])

        self._required_string(event, "event_id", errors)

        event_type = event.get("event_type")
        if not isinstance(event_type, str) or not event_type.strip():
            errors.append("event_type must be a non-empty string.")
        elif event_type not in PAYLOAD_SCHEMAS:
            errors.append(f"Unsupported event_type: {event_type!r}.")

        if type(event.get("event_version")) is not int:
            errors.append("event_version must be an integer.")

        self._validate_timestamp(event.get("event_time"), errors)

        processing = event.get("processing")
        if not isinstance(processing, dict):
            errors.append("processing must be an object.")
        else:
            targets = processing.get("targets")
            if not isinstance(targets, list) or not targets:
                errors.append("processing.targets must be a non-empty array.")
            else:
                invalid = [value for value in targets if value not in ALLOWED_TARGETS]
                if invalid:
                    errors.append(
                        "processing.targets contains invalid values: "
                        + ", ".join(repr(value) for value in invalid)
                    )
                if len(set(targets)) != len(targets):
                    errors.append("processing.targets must not contain duplicates.")

                if (
                    isinstance(event_type, str)
                    and event_type in EXPECTED_TARGETS
                    and not invalid
                    and set(targets) != EXPECTED_TARGETS[event_type]
                ):
                    errors.append(
                        f"processing.targets for {event_type} must be "
                        f"{sorted(EXPECTED_TARGETS[event_type])}; received {sorted(set(targets))}."
                    )

        self._validate_customer(event.get("customer"), errors)

        session = event.get("session")
        if not isinstance(session, dict):
            errors.append("session must be an object.")
        else:
            self._required_string(session, "session_id", errors, prefix="session.")

        device = event.get("device")
        if not isinstance(device, dict):
            errors.append("device must be an object.")
        else:
            for field in ("device_type", "os", "browser"):
                self._required_string(device, field, errors, prefix="device.")

            device_type = device.get("device_type")
            if (
                isinstance(device_type, str)
                and device_type.strip()
                and device_type not in {"mobile", "desktop", "tablet"}
            ):
                errors.append(
                    "device.device_type must be one of: mobile, desktop, tablet."
                )

        source = event.get("source")
        if not isinstance(source, dict):
            errors.append("source must be an object.")
        else:
            for field in ("channel", "page"):
                self._required_string(source, field, errors, prefix="source.")

            if "referrer" not in source:
                errors.append("source.referrer is required.")
            elif source["referrer"] is not None and not isinstance(
                source["referrer"], str
            ):
                errors.append("source.referrer must be a string or null.")

        payload = event.get("payload")
        if not isinstance(payload, dict):
            errors.append("payload must be an object.")
        elif isinstance(event_type, str) and event_type in PAYLOAD_SCHEMAS:
            self._validate_payload(event_type, payload, errors)

        return ValidationResult(valid=not errors, errors=errors)

    def _validate_customer(self, customer: Any, errors: list[str]) -> None:
        if not isinstance(customer, dict):
            errors.append("customer must be an object.")
            return

        for field in ("customer_id", "anonymous_id"):
            if field not in customer:
                errors.append(f"customer.{field} is required.")

        if "customer_id" not in customer or "anonymous_id" not in customer:
            return

        customer_id = customer.get("customer_id")
        anonymous_id = customer.get("anonymous_id")

        if customer_id is not None and not self._is_nonempty_string(customer_id):
            errors.append("customer.customer_id must be a string or null.")
        if anonymous_id is not None and not self._is_nonempty_string(anonymous_id):
            errors.append("customer.anonymous_id must be a string or null.")

        has_customer = self._is_nonempty_string(customer_id)
        has_anonymous = self._is_nonempty_string(anonymous_id)
        if has_customer == has_anonymous:
            errors.append(
                "Exactly one of customer.customer_id or customer.anonymous_id "
                "must be populated."
            )

    def _validate_payload(
        self,
        event_type: str,
        payload: dict[str, Any],
        errors: list[str],
    ) -> None:
        schema = PAYLOAD_SCHEMAS[event_type]

        for field, expected_type in schema.items():
            if field not in payload:
                errors.append(f"payload.{field} is required for {event_type}.")
                continue

            if not self._matches_type(payload[field], expected_type):
                errors.append(
                    f"payload.{field} has invalid type for {event_type}."
                )

        if event_type == "search_no_results" and payload.get("results_count") != 0:
            errors.append("search_no_results.results_count must be 0.")

        if event_type == "product_favorite":
            action = payload.get("action")
            if isinstance(action, str) and action not in {"add", "remove"}:
                errors.append("product_favorite.action must be 'add' or 'remove'.")

        if event_type == "login" and type(payload.get("success")) is bool:
            success = payload["success"]
            failure_reason = payload.get("failure_reason")
            if success and failure_reason is not None:
                errors.append(
                    "login.failure_reason must be null when login.success is true."
                )
            if not success and not self._is_nonempty_string(failure_reason):
                errors.append(
                    "login.failure_reason must be populated when login.success is false."
                )

        if event_type == "purchase" and isinstance(payload.get("items"), list):
            items = payload["items"]
            if not items:
                errors.append("purchase.items must contain at least one item.")

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"purchase.items[{index}] must be an object.")
                    continue

                item_schema = {
                    "product_id": str,
                    "quantity": int,
                    "unit_price": "number",
                }
                for field, expected_type in item_schema.items():
                    if field not in item:
                        errors.append(f"purchase.items[{index}].{field} is required.")
                    elif not self._matches_type(item[field], expected_type):
                        errors.append(
                            f"purchase.items[{index}].{field} has invalid type."
                        )

        for field in (
            "quantity",
            "items_count",
            "results_count",
            "duration_seconds",
            "pages_viewed",
            "products_viewed",
            "items_added_to_cart",
        ):
            if field in payload and type(payload[field]) is int and payload[field] < 0:
                errors.append(f"payload.{field} cannot be negative.")

        for field in (
            "unit_price",
            "total_amount",
            "shipping_cost",
            "cart_value",
            "amount",
        ):
            value = payload.get(field)
            if type(value) in {int, float} and value < 0:
                errors.append(f"payload.{field} cannot be negative.")

    @staticmethod
    def _matches_type(value: Any, expected_type: Any) -> bool:
        if expected_type == "number":
            return type(value) in {int, float}
        if expected_type == "nullable_string":
            return value is None or EventValidator._is_nonempty_string(value)
        if expected_type is int:
            return type(value) is int
        if expected_type is bool:
            return type(value) is bool
        if expected_type is str:
            return EventValidator._is_nonempty_string(value)
        return isinstance(value, expected_type)

    @staticmethod
    def _is_nonempty_string(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _required_string(
        mapping: dict[str, Any],
        field: str,
        errors: list[str],
        *,
        prefix: str = "",
    ) -> None:
        if field not in mapping:
            errors.append(f"{prefix}{field} is required.")
        elif not EventValidator._is_nonempty_string(mapping[field]):
            errors.append(f"{prefix}{field} must be a non-empty string.")

    @staticmethod
    def _validate_timestamp(value: Any, errors: list[str]) -> None:
        if not isinstance(value, str) or not value.strip():
            errors.append("event_time must be a non-empty ISO 8601 string.")
            return

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                errors.append("event_time must include a timezone.")
        except ValueError:
            errors.append("event_time must be a valid ISO 8601 timestamp.")
