"""Generate coherent user sessions instead of independent random events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random

from config import settings
from simulator.data_catalog import DataCatalog, Product
from simulator.event_generator import EventGenerator
from simulator import payload_generators as payloads


@dataclass
class EventDraft:
    event_type: str
    payload: dict
    customer: dict
    source_page: str
    source_referrer: str | None
    offset_seconds: int


class SessionBuilder:
    """Mutable helper used to build one coherent session."""

    def __init__(self, catalog: DataCatalog, rng: random.Random) -> None:
        self.catalog = catalog
        self.rng = rng
        self.session_id = EventGenerator.new_session_id()
        self.cart_id = EventGenerator.new_cart_id()
        self.order_id: str | None = None
        self.cart: dict[str, dict] = {}
        self.customer = self._customer()
        self.device = self._device()
        self.channel = "web"
        self.current_page = "/home"
        self.previous_page: str | None = None
        self.elapsed_seconds = 0
        self.pages_viewed = 0
        self.products_viewed: set[str] = set()
        self.items_added_to_cart = 0
        self.purchase_completed = False
        self.events: list[EventDraft] = []

    def _customer(self) -> dict:
        if self.rng.random() < settings.REGISTERED_USER_PROBABILITY:
            customer_number = self.rng.randint(1, settings.REGISTERED_CUSTOMER_POOL_SIZE)
            return {
                "customer_id": f"cus_{customer_number:05d}",
                "anonymous_id": None,
            }
        return {
            "customer_id": None,
            "anonymous_id": EventGenerator.new_anonymous_id(),
        }

    def _device(self) -> dict:
        device_types = list(settings.DEVICE_WEIGHTS)
        weights = list(settings.DEVICE_WEIGHTS.values())
        device_type = self.rng.choices(device_types, weights=weights, k=1)[0]

        if device_type == "mobile":
            os_name = self.rng.choice(["Android", "iOS"])
            browser = "Safari" if os_name == "iOS" and self.rng.random() < 0.70 else "Chrome"
        elif device_type == "tablet":
            os_name = self.rng.choice(["Android", "iOS"])
            browser = "Safari" if os_name == "iOS" else "Chrome"
        else:
            os_name = self.rng.choice(["Windows", "macOS"])
            if os_name == "macOS":
                browser = self.rng.choice(["Safari", "Chrome", "Firefox"])
            else:
                browser = self.rng.choice(["Chrome", "Firefox"])

        return {"device_type": device_type, "os": os_name, "browser": browser}

    def _advance_time(self) -> None:
        self.elapsed_seconds += self.rng.randint(
            settings.MIN_DWELL_SECONDS,
            settings.MAX_DWELL_SECONDS,
        )

    def emit(self, event_type: str, payload: dict, *, advance_time: bool = True) -> None:
        self.events.append(
            EventDraft(
                event_type=event_type,
                payload=payload,
                customer=dict(self.customer),
                source_page=self.current_page,
                source_referrer=self.previous_page,
                offset_seconds=self.elapsed_seconds,
            )
        )
        if advance_time:
            self._advance_time()

    def navigate(self, page: str, page_type: str) -> None:
        self.previous_page = self.current_page
        self.current_page = page
        self.emit("page_view", payloads.page_view(page, page_type))
        self.pages_viewed += 1

    def start(self, landing_page: str = "/home") -> None:
        self.current_page = landing_page
        self.previous_page = None
        self.emit("session_started", payloads.session_started(landing_page))
        self.emit("page_view", payloads.page_view(landing_page, self._page_type(landing_page)))
        self.pages_viewed += 1

    @staticmethod
    def _page_type(page: str) -> str:
        if page == "/home":
            return "home"
        if page.startswith("/categories/"):
            return "category"
        if page.startswith("/products/"):
            return "product"
        if page.startswith("/search"):
            return "search"
        if page == "/login":
            return "login"
        if page == "/cart":
            return "cart"
        if page.startswith("/checkout"):
            return "checkout"
        if page.startswith("/orders/"):
            return "order_confirmation"
        return "other"

    def maybe_login(self) -> None:
        """Simulate an authentication attempt for sessions that started anonymous.

        The login event preserves the anonymous identity that initiated the attempt.
        If authentication succeeds, only subsequent events in the same session switch
        to a registered customer_id. This keeps the pre-login and post-login behavior
        linkable through the common session_id without placing both identifiers in the
        same customer object.
        """
        if self.customer.get("customer_id") is not None:
            return
        if self.rng.random() >= settings.LOGIN_ATTEMPT_PROBABILITY:
            return

        login_method = self.rng.choices(
            list(settings.LOGIN_METHOD_WEIGHTS),
            weights=list(settings.LOGIN_METHOD_WEIGHTS.values()),
            k=1,
        )[0]
        success = self.rng.random() < settings.LOGIN_SUCCESS_PROBABILITY
        failure_reason = None
        if not success:
            failure_reason = self.rng.choices(
                list(settings.LOGIN_FAILURE_REASON_WEIGHTS),
                weights=list(settings.LOGIN_FAILURE_REASON_WEIGHTS.values()),
                k=1,
            )[0]

        self.navigate("/login", "login")
        self.emit(
            "login",
            payloads.login(
                login_method=login_method,
                success=success,
                ip_country=settings.LOGIN_IP_COUNTRY,
                failure_reason=failure_reason,
            ),
        )

        if success:
            customer_number = self.rng.randint(1, settings.REGISTERED_CUSTOMER_POOL_SIZE)
            self.customer = {
                "customer_id": f"cus_{customer_number:05d}",
                "anonymous_id": None,
            }

    def visit_category(self) -> None:
        category = self.catalog.random_category(self.rng)
        self.navigate(f"/categories/{category.category_id}", "category")
        self.emit("category_view", payloads.category_view(category.category_id))

    def visit_product(self, product: Product | None = None) -> Product:
        product = product or self.catalog.random_product(self.rng)
        self.navigate(f"/products/{product.product_id}", "product")
        self.emit("product_view", payloads.product_view(product))
        self.products_viewed.add(product.product_id)
        return product

    def perform_search(self) -> Product | None:
        no_results = self.rng.random() < settings.SEARCH_NO_RESULTS_PROBABILITY
        if no_results:
            query = self.catalog.no_results_query(self.rng)
            self.navigate(f"/search?q={query.replace(' ', '+')}", "search")
            self.emit("search_no_results", payloads.search_no_results(query))
            return None

        product = self.catalog.random_product(self.rng)
        query = self.catalog.search_query_for_product(product)
        results_count = self.rng.randint(1, 20)
        self.navigate(f"/search?q={query.replace(' ', '+')}", "search")
        self.emit("search", payloads.search(query, results_count))
        return product

    def interact_with_product(self, product: Product) -> None:
        if self.rng.random() < settings.FAVORITE_PROBABILITY:
            self.emit(
                "product_favorite",
                payloads.product_favorite(product.product_id, self.rng.choice(["add", "remove"])),
            )

        if self.rng.random() < settings.SHARE_PROBABILITY:
            self.emit(
                "product_share",
                payloads.product_share(product.product_id, self.rng.choice(settings.SHARE_PLATFORMS)),
            )

        if self.rng.random() < settings.ADD_TO_CART_PROBABILITY:
            quantity = self.rng.randint(1, 3)
            existing = self.cart.setdefault(
                product.product_id,
                {"quantity": 0, "unit_price": product.unit_price},
            )
            existing["quantity"] += quantity
            self.items_added_to_cart += quantity
            self.emit("add_to_cart", payloads.add_to_cart(product, quantity))

    def maybe_remove_from_cart(self) -> None:
        if not self.cart or self.rng.random() >= settings.REMOVE_FROM_CART_PROBABILITY:
            return

        product_id = self.rng.choice(list(self.cart))
        current_quantity = self.cart[product_id]["quantity"]
        quantity = self.rng.randint(1, current_quantity)
        self.emit("remove_from_cart", payloads.remove_from_cart(product_id, quantity))
        self.cart[product_id]["quantity"] -= quantity
        if self.cart[product_id]["quantity"] <= 0:
            del self.cart[product_id]

    def maybe_view_cart(self) -> None:
        if self.cart and self.rng.random() < settings.VIEW_CART_PROBABILITY:
            self.navigate("/cart", "cart")
            self.emit("cart_view", payloads.cart_view(self.cart_id, self.cart))

    def maybe_checkout(self) -> None:
        if not self.cart or self.rng.random() >= settings.CHECKOUT_PROBABILITY_GIVEN_CART:
            return

        self.order_id = EventGenerator.new_order_id()
        self.navigate("/checkout", "checkout")
        self.emit("checkout_started", payloads.checkout_started(self.order_id, self.cart))

        outcome = self.rng.choices(
            list(settings.CHECKOUT_OUTCOME_WEIGHTS),
            weights=list(settings.CHECKOUT_OUTCOME_WEIGHTS.values()),
            k=1,
        )[0]

        cart_value = payloads.cart_total(self.cart)

        if outcome == "abandoned":
            step = self.rng.choice(settings.CHECKOUT_ABANDON_STEPS)
            if step in {"payment", "review"}:
                shipping_method = self.rng.choice(list(settings.SHIPPING_METHODS))
                shipping_cost = settings.SHIPPING_METHODS[shipping_method]
                self.navigate("/checkout/shipping", "checkout")
                self.emit(
                    "checkout_shipping",
                    payloads.checkout_shipping(self.order_id, shipping_method, shipping_cost),
                )
            if step == "review":
                payment_method = self.rng.choice(settings.PAYMENT_METHODS)
                self.navigate("/checkout/payment", "checkout")
                self.emit("checkout_payment", payloads.checkout_payment(self.order_id, payment_method))
            self.emit(
                "checkout_abandoned",
                payloads.checkout_abandoned(self.order_id, step, cart_value),
            )
            return

        shipping_method = self.rng.choice(list(settings.SHIPPING_METHODS))
        shipping_cost = settings.SHIPPING_METHODS[shipping_method]
        self.navigate("/checkout/shipping", "checkout")
        self.emit(
            "checkout_shipping",
            payloads.checkout_shipping(self.order_id, shipping_method, shipping_cost),
        )

        payment_method = self.rng.choice(settings.PAYMENT_METHODS)
        self.navigate("/checkout/payment", "checkout")
        self.emit("checkout_payment", payloads.checkout_payment(self.order_id, payment_method))

        amount = cart_value + shipping_cost
        if outcome == "payment_failed":
            error_code = self.rng.choice(settings.PAYMENT_ERROR_CODES)
            self.emit(
                "payment_failed",
                payloads.payment_failed(self.order_id, payment_method, amount, error_code),
            )
            if self.rng.random() < settings.CANCEL_AFTER_PAYMENT_FAILURE_PROBABILITY:
                self.emit(
                    "order_cancelled",
                    payloads.order_cancelled(self.order_id, "payment_failed"),
                )
            return

        # Successful payment completes the purchase. The payment payload amount and
        # purchase total are kept consistent and include the selected shipping cost.
        self.emit(
            "payment_success",
            payloads.payment_success(self.order_id, payment_method, amount),
        )
        self.navigate(f"/orders/{self.order_id}/confirmation", "order_confirmation")
        self.emit("purchase", payloads.purchase(self.order_id, self.cart, amount))
        self.purchase_completed = True

    def finish(self) -> None:
        self.emit(
            "session_ended",
            payloads.session_ended(
                duration_seconds=max(1, self.elapsed_seconds),
                pages_viewed=self.pages_viewed,
                products_viewed=len(self.products_viewed),
                items_added_to_cart=self.items_added_to_cart,
                purchase_completed=self.purchase_completed,
            ),
            advance_time=False,
        )

    def build_events(self) -> list[dict]:
        """Materialize drafts into the documented common event envelope.

        The synthetic timestamps are internally coherent: the final event occurs at
        approximately the generation time, and earlier events are placed in the past
        according to the simulated dwell time accumulated in the session.
        """
        end_time = datetime.now(timezone.utc)
        total_duration = max(1, self.elapsed_seconds)
        start_time = end_time - timedelta(seconds=total_duration)

        return [
            EventGenerator.build(
                event_type=draft.event_type,
                customer=draft.customer,
                session_id=self.session_id,
                device=self.device,
                source={
                    "channel": self.channel,
                    "page": draft.source_page,
                    "referrer": draft.source_referrer,
                },
                payload=draft.payload,
                event_time=start_time + timedelta(seconds=draft.offset_seconds),
            )
            for draft in self.events
        ]


class SessionGenerator:
    def __init__(self, catalog: DataCatalog, rng: random.Random) -> None:
        self.catalog = catalog
        self.rng = rng

    def generate(self) -> list[dict]:
        builder = SessionBuilder(self.catalog, self.rng)
        builder.start("/home")
        builder.maybe_login()

        browsing_actions = self.rng.randint(
            settings.MIN_BROWSING_ACTIONS,
            settings.MAX_BROWSING_ACTIONS,
        )

        for _ in range(browsing_actions):
            if self.rng.random() < settings.SEARCH_PROBABILITY:
                product = builder.perform_search()
                if product is not None and self.rng.random() < 0.70:
                    product = builder.visit_product(product)
                    builder.interact_with_product(product)
            else:
                if self.rng.random() < 0.35:
                    builder.visit_category()
                product = builder.visit_product()
                builder.interact_with_product(product)

        builder.maybe_remove_from_cart()
        builder.maybe_view_cart()
        builder.maybe_checkout()
        builder.finish()
        return builder.build_events()

    def generate_exact_browsing_session(self, target_length: int) -> list[dict]:
        """Generate a complete session with exactly target_length events.

        This is used only to satisfy the requested exact global event count without
        cutting a session in half. It keeps a valid session_started/page_view/.../
        session_ended structure and fills the middle with coherent browsing events.
        """
        if target_length < 3:
            raise ValueError("A complete session needs at least 3 events.")

        builder = SessionBuilder(self.catalog, self.rng)
        builder.start("/home")  # 2 events

        # Reserve one final slot for session_ended.
        middle_slots = target_length - 3

        # A login attempt naturally adds page_view(/login) + login. Include it in
        # exact-length sessions only when there is enough room, then account for the
        # slots it consumed so the requested total remains exact.
        if middle_slots >= 2:
            events_before_login = len(builder.events)
            builder.maybe_login()
            middle_slots -= len(builder.events) - events_before_login

        while middle_slots > 0:
            if middle_slots >= 2 and self.rng.random() < 0.65:
                product = self.catalog.random_product(self.rng)
                # A product visit naturally produces page_view + product_view.
                builder.visit_product(product)
                middle_slots -= 2
            else:
                # page_view alone is valid because the contract states it fires on any page.
                page = self.rng.choice(["/home", "/cart", "/help", "/offers"])
                builder.navigate(page, builder._page_type(page))
                middle_slots -= 1

        builder.finish()
        events = builder.build_events()
        if len(events) != target_length:
            raise AssertionError("Exact session generation produced an unexpected length.")
        return events
