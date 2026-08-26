"""Payload builders for every documented event_type."""

from __future__ import annotations

from typing import Iterable

from config.settings import CURRENCY
from simulator.data_catalog import Product


def page_view(page: str, page_type: str) -> dict:
    return {"page": page, "page_type": page_type}


def category_view(category_id: str) -> dict:
    return {"category_id": category_id}


def product_view(product: Product) -> dict:
    return {"product_id": product.product_id, "category_id": product.category_id}


def search(query: str, results_count: int) -> dict:
    return {"query": query, "results_count": results_count}


def search_no_results(query: str) -> dict:
    return {"query": query, "results_count": 0}


def product_favorite(product_id: str, action: str) -> dict:
    return {"product_id": product_id, "action": action}


def product_share(product_id: str, platform: str) -> dict:
    return {"product_id": product_id, "platform": platform}


def add_to_cart(product: Product, quantity: int) -> dict:
    return {
        "product_id": product.product_id,
        "quantity": quantity,
        "unit_price": product.unit_price,
        "currency": CURRENCY,
    }


def remove_from_cart(product_id: str, quantity: int) -> dict:
    return {"product_id": product_id, "quantity": quantity}


def cart_view(cart_id: str, cart: dict[str, dict]) -> dict:
    return {
        "cart_id": cart_id,
        "items_count": len(cart),
        "total_amount": cart_total(cart),
        "currency": CURRENCY,
    }


def checkout_started(order_id: str, cart: dict[str, dict]) -> dict:
    return {
        "order_id": order_id,
        "items_count": sum(item["quantity"] for item in cart.values()),
        "total_amount": cart_total(cart),
        "currency": CURRENCY,
    }


def checkout_shipping(order_id: str, shipping_method: str, shipping_cost: int) -> dict:
    return {
        "order_id": order_id,
        "shipping_method": shipping_method,
        "shipping_cost": shipping_cost,
        "currency": CURRENCY,
    }


def checkout_payment(order_id: str, payment_method: str) -> dict:
    return {"order_id": order_id, "payment_method": payment_method}


def checkout_abandoned(order_id: str, step: str, cart_value: int) -> dict:
    return {
        "order_id": order_id,
        "step": step,
        "cart_value": cart_value,
        "currency": CURRENCY,
    }


def purchase(order_id: str, cart: dict[str, dict], total_amount: int) -> dict:
    items = [
        {
            "product_id": product_id,
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
        }
        for product_id, item in cart.items()
    ]
    return {
        "order_id": order_id,
        "total_amount": total_amount,
        "currency": CURRENCY,
        "items": items,
    }


def payment_success(order_id: str, payment_method: str, amount: int) -> dict:
    return {
        "order_id": order_id,
        "payment_method": payment_method,
        "amount": amount,
        "currency": CURRENCY,
    }


def payment_failed(
    order_id: str,
    payment_method: str,
    amount: int,
    error_code: str,
) -> dict:
    return {
        "order_id": order_id,
        "payment_method": payment_method,
        "amount": amount,
        "currency": CURRENCY,
        "error_code": error_code,
    }


def order_cancelled(order_id: str, reason: str) -> dict:
    return {"order_id": order_id, "reason": reason}


def session_started(landing_page: str) -> dict:
    return {"landing_page": landing_page}


def session_ended(
    duration_seconds: int,
    pages_viewed: int,
    products_viewed: int,
    items_added_to_cart: int,
    purchase_completed: bool,
) -> dict:
    return {
        "duration_seconds": duration_seconds,
        "pages_viewed": pages_viewed,
        "products_viewed": products_viewed,
        "items_added_to_cart": items_added_to_cart,
        "purchase_completed": purchase_completed,
    }


def login(
    login_method: str,
    success: bool,
    ip_country: str,
    failure_reason: str | None,
) -> dict:
    return {
        "login_method": login_method,
        "success": success,
        "ip_country": ip_country,
        "failure_reason": failure_reason,
    }


def cart_total(cart: dict[str, dict]) -> int:
    return sum(item["quantity"] * item["unit_price"] for item in cart.values())
