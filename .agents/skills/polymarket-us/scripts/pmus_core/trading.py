from __future__ import annotations

from dataclasses import dataclass

from .confirmation import ConfirmationStore


class AmbiguousMutationError(RuntimeError):
    def __init__(self, message: str, recovery: str) -> None:
        super().__init__(message)
        self.ambiguous = True
        self.retry_safe = False
        self.recovery = recovery


def _is_ambiguous(exc: Exception) -> bool:
    return exc.__class__.__name__ in {
        "APITimeoutError",
        "APIConnectionError",
        "TimeoutError",
        "ConnectionError",
    }


def _mutate(call, *, recovery: str):
    try:
        return call()
    except Exception as exc:
        if _is_ambiguous(exc):
            raise AmbiguousMutationError(str(exc) or exc.__class__.__name__, recovery) from exc
        raise


def preview_create(
    client: object,
    request: dict[str, object],
    store: ConfirmationStore,
) -> dict[str, object]:
    preview = client.orders.preview({"request": request})
    issued = store.issue("orders.create", request, {"preview": preview})
    return {
        "preview": preview,
        "normalizedRequest": request,
        "confirmationToken": issued.token,
        "expiresAt": issued.expires_at,
    }


def prepare_modify(
    client: object,
    order_id: str,
    request: dict[str, object],
    store: ConfirmationStore,
) -> dict[str, object]:
    current = client.orders.retrieve(order_id)
    payload = {"orderId": order_id, "request": request}
    issued = store.issue("orders.modify", payload, {"currentOrder": current})
    return {
        "currentOrder": current,
        "requestedChanges": request,
        "confirmationToken": issued.token,
        "expiresAt": issued.expires_at,
    }


def modify_order(
    client: object,
    order_id: str,
    request: dict[str, object],
    token: str,
    store: ConfirmationStore,
) -> dict[str, object]:
    payload = {"orderId": order_id, "request": request}
    store.consume(token, "orders.modify", payload)
    _mutate(
        lambda: client.orders.modify(order_id, request),
        recovery=f"Run `orders get {order_id}` before considering another modification.",
    )
    return {"orderId": order_id, "modified": True}


def prepare_cancel(
    client: object,
    order_id: str,
    market_slug: str,
    store: ConfirmationStore,
) -> dict[str, object]:
    current = client.orders.retrieve(order_id)
    payload = {"orderId": order_id, "marketSlug": market_slug}
    issued = store.issue("orders.cancel", payload, {"currentOrder": current})
    return {
        "currentOrder": current,
        "marketSlug": market_slug,
        "confirmationToken": issued.token,
        "expiresAt": issued.expires_at,
    }


def cancel_order(
    client: object,
    order_id: str,
    market_slug: str,
    token: str,
    store: ConfirmationStore,
) -> dict[str, object]:
    payload = {"orderId": order_id, "marketSlug": market_slug}
    store.consume(token, "orders.cancel", payload)
    _mutate(
        lambda: client.orders.cancel(order_id, {"marketSlug": market_slug}),
        recovery=f"Run `orders get {order_id}` to inspect whether the cancel took effect.",
    )
    return {"orderId": order_id, "marketSlug": market_slug, "canceled": True}


def prepare_cancel_all(
    client: object,
    slugs: list[str] | None,
    store: ConfirmationStore,
) -> dict[str, object]:
    normalized_slugs = slugs or []
    params = {"slugs": normalized_slugs} if normalized_slugs else None
    current = client.orders.list(params)
    payload = {"slugs": normalized_slugs}
    issued = store.issue("orders.cancel-all", payload, {"openOrders": current})
    return {
        "openOrders": current,
        "slugs": normalized_slugs,
        "confirmationToken": issued.token,
        "expiresAt": issued.expires_at,
    }


def cancel_all_orders(
    client: object,
    slugs: list[str] | None,
    token: str,
    store: ConfirmationStore,
) -> object:
    normalized_slugs = slugs or []
    payload = {"slugs": normalized_slugs}
    store.consume(token, "orders.cancel-all", payload)
    params = {"slugs": normalized_slugs} if normalized_slugs else None
    return _mutate(
        lambda: client.orders.cancel_all(params),
        recovery="Run `orders list` to inspect which orders remain open.",
    )


def prepare_close_position(
    client: object,
    request: dict[str, object],
    store: ConfirmationStore,
) -> dict[str, object]:
    slug = request.get("marketSlug")
    params = {"slugs": [slug]} if isinstance(slug, str) and slug else None
    positions = client.portfolio.positions(params)
    issued = store.issue("positions.close", request, {"positions": positions})
    return {
        "positions": positions,
        "request": request,
        "confirmationToken": issued.token,
        "expiresAt": issued.expires_at,
    }


def close_position(
    client: object,
    request: dict[str, object],
    token: str,
    store: ConfirmationStore,
) -> object:
    store.consume(token, "positions.close", request)
    return _mutate(
        lambda: client.orders.close_position(request),
        recovery="Run `portfolio positions` to inspect the current position before considering another close.",
    )


def create_order(
    client: object,
    request: dict[str, object],
    token: str,
    store: ConfirmationStore,
) -> object:
    store.consume(token, "orders.create", request)
    return _mutate(
        lambda: client.orders.create(request),
        recovery="Run `orders list` for the market and inspect current position before considering a retry.",
    )
