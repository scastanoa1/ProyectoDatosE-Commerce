"""Configurable simulation assumptions.

The event contracts come from the project Markdown documentation. The probabilities
below are simulation defaults chosen to produce plausible e-commerce behavior. They
are configurable assumptions, not claimed to be universal market statistics.
"""

EVENT_VERSION = 1
CURRENCY = "COP"

# All events are published to the same ingress (Pub/Sub). These targets are metadata
# used downstream to route/process each event according to its documented contract.
EVENT_TARGETS = {
    "page_view": ["batch"],
    "category_view": ["batch"],
    "product_view": ["batch", "streaming"],
    "search": ["batch", "streaming"],
    "search_no_results": ["batch"],
    "product_favorite": ["batch", "streaming"],
    "product_share": ["batch"],
    "add_to_cart": ["batch", "streaming"],
    "remove_from_cart": ["batch", "streaming"],
    "cart_view": ["batch"],
    "checkout_started": ["batch"],
    "checkout_shipping": ["batch"],
    "checkout_payment": ["batch"],
    "checkout_abandoned": ["batch"],
    "purchase": ["batch", "streaming"],
    "payment_success": ["batch", "streaming"],
    "payment_failed": ["batch", "streaming"],
    "order_cancelled": ["batch"],
    "session_started": ["batch"],
    "session_ended": ["batch"],
    "login": ["batch", "streaming"],
}

# Synthetic behavioral assumptions (configurable).
REGISTERED_USER_PROBABILITY = 0.35
DEVICE_WEIGHTS = {
    "mobile": 0.60,
    "desktop": 0.35,
    "tablet": 0.05,
}

# Login behavior.
# Only sessions that start anonymous can generate a login attempt. A successful login
# changes subsequent events in the same session to a registered customer while the
# login event itself still carries the anonymous identity that initiated the attempt.
LOGIN_ATTEMPT_PROBABILITY = 0.20
LOGIN_SUCCESS_PROBABILITY = 0.92
LOGIN_METHOD_WEIGHTS = {
    "email": 0.72,
    "google": 0.28,
}
LOGIN_FAILURE_REASON_WEIGHTS = {
    "invalid_password": 0.85,
    "account_locked": 0.15,
}
# The current simulated business context uses COP and Colombian data-protection rules,
# so login IP country is kept as Colombia until a multi-country scenario is defined.
LOGIN_IP_COUNTRY = "CO"

# Navigation/action probabilities.
SEARCH_PROBABILITY = 0.30
SEARCH_NO_RESULTS_PROBABILITY = 0.12
FAVORITE_PROBABILITY = 0.10
SHARE_PROBABILITY = 0.05
ADD_TO_CART_PROBABILITY = 0.22
REMOVE_FROM_CART_PROBABILITY = 0.10
VIEW_CART_PROBABILITY = 0.80
CHECKOUT_PROBABILITY_GIVEN_CART = 0.38

# Outcome probabilities once checkout has started. Must sum to 1.0.
CHECKOUT_OUTCOME_WEIGHTS = {
    "success": 0.65,
    "abandoned": 0.25,
    "payment_failed": 0.10,
}

# A failed payment may end in an order cancellation.
CANCEL_AFTER_PAYMENT_FAILURE_PROBABILITY = 0.55

# Session shape.
MIN_BROWSING_ACTIONS = 2
MAX_BROWSING_ACTIONS = 6
MIN_DWELL_SECONDS = 2
MAX_DWELL_SECONDS = 18

# Synthetic method/value domains supported by the payload documentation examples.
SHIPPING_METHODS = {
    "standard": 12000,
    "express": 22000,
}
PAYMENT_METHODS = ["credit_card", "pse", "cash_on_delivery"]
PAYMENT_ERROR_CODES = ["PAYMENT_DECLINED", "INSUFFICIENT_FUNDS"]
ORDER_CANCEL_REASONS = ["customer_request", "out_of_stock", "payment_failed"]
SHARE_PLATFORMS = ["whatsapp", "facebook", "email"]
CHECKOUT_ABANDON_STEPS = ["shipping", "payment", "review"]

# Pools for repeated synthetic registered customers.
REGISTERED_CUSTOMER_POOL_SIZE = 250
