from __future__ import annotations

import pytest


class APITimeoutError(Exception):
    pass


class FakeOrders:
    def __init__(self) -> None:
        self.create_calls = []
        self.modify_calls = []
        self.cancel_calls = []
        self.cancel_all_calls = []
        self.close_calls = []
        self.retrieve_result = {"order": {"id": "ord-1", "marketSlug": "m", "state": "ORDER_STATE_NEW"}}
        self.list_result = {"orders": [{"id": "ord-1", "marketSlug": "m"}]}
        self.create_error = None

    def create(self, request):
        self.create_calls.append(request)
        if self.create_error:
            raise self.create_error
        return {"id": "new-1"}

    def modify(self, order_id, request):
        self.modify_calls.append((order_id, request))
        return None

    def cancel(self, order_id, request):
        self.cancel_calls.append((order_id, request))
        return None

    def cancel_all(self, request=None):
        self.cancel_all_calls.append(request)
        return {"canceledOrderIds": ["ord-1"]}

    def close_position(self, request):
        self.close_calls.append(request)
        return {"id": "close-1"}

    def retrieve(self, order_id):
        return self.retrieve_result

    def list(self, params=None):
        return self.list_result


class FakePortfolio:
    def positions(self, params=None):
        return {"positions": [{"marketSlug": "m", "quantity": 2}]}


class FakeClient:
    def __init__(self) -> None:
        self.orders = FakeOrders()
        self.portfolio = FakePortfolio()


def make_store(tmp_path):
    from pmus_core.confirmation import ConfirmationStore

    return ConfirmationStore(root=tmp_path, ttl_seconds=300, clock=lambda: 1000.0)


def test_create_requires_matching_token_and_invokes_once(tmp_path) -> None:
    from pmus_core.confirmation import ConfirmationError
    from pmus_core.trading import create_order

    client = FakeClient()
    store = make_store(tmp_path)
    request = {"marketSlug": "m", "intent": "ORDER_INTENT_BUY_LONG", "quantity": 2}

    with pytest.raises(ConfirmationError):
        create_order(client, request, "missing", store)
    assert client.orders.create_calls == []

    token = store.issue("orders.create", request).token
    result = create_order(client, request, token, store)
    assert result == {"id": "new-1"}
    assert client.orders.create_calls == [request]

    with pytest.raises(ConfirmationError):
        create_order(client, request, token, store)
    assert client.orders.create_calls == [request]


def test_mismatched_create_payload_never_calls_sdk(tmp_path) -> None:
    from pmus_core.confirmation import ConfirmationError
    from pmus_core.trading import create_order

    client = FakeClient()
    store = make_store(tmp_path)
    original = {"marketSlug": "m", "intent": "ORDER_INTENT_BUY_LONG", "quantity": 2}
    token = store.issue("orders.create", original).token

    with pytest.raises(ConfirmationError):
        create_order(client, {**original, "quantity": 3}, token, store)
    assert client.orders.create_calls == []


def test_prepare_modify_binds_current_order_and_requested_change(tmp_path) -> None:
    from pmus_core.trading import modify_order, prepare_modify

    client = FakeClient()
    store = make_store(tmp_path)
    request = {"marketSlug": "m", "price": {"value": "0.60", "currency": "USD"}}

    prepared = prepare_modify(client, "ord-1", request, store)
    result = modify_order(client, "ord-1", request, prepared["confirmationToken"], store)

    assert prepared["currentOrder"]["order"]["id"] == "ord-1"
    assert result == {"orderId": "ord-1", "modified": True}
    assert client.orders.modify_calls == [("ord-1", request)]


def test_prepare_cancel_cancel_all_and_close_position(tmp_path) -> None:
    from pmus_core.trading import (
        cancel_all_orders,
        cancel_order,
        close_position,
        prepare_cancel,
        prepare_cancel_all,
        prepare_close_position,
    )

    client = FakeClient()
    store = make_store(tmp_path)

    cancel = prepare_cancel(client, "ord-1", "m", store)
    assert cancel_order(client, "ord-1", "m", cancel["confirmationToken"], store)["canceled"] is True

    cancel_all = prepare_cancel_all(client, ["m"], store)
    assert cancel_all_orders(client, ["m"], cancel_all["confirmationToken"], store) == {
        "canceledOrderIds": ["ord-1"]
    }

    request = {"marketSlug": "m"}
    close = prepare_close_position(client, request, store)
    assert close_position(client, request, close["confirmationToken"], store) == {"id": "close-1"}

    assert client.orders.cancel_calls == [("ord-1", {"marketSlug": "m"})]
    assert client.orders.cancel_all_calls == [{"slugs": ["m"]}]
    assert client.orders.close_calls == [request]


def test_timeout_after_token_consumption_is_ambiguous_and_not_retried(tmp_path) -> None:
    from pmus_core.trading import AmbiguousMutationError, create_order

    client = FakeClient()
    client.orders.create_error = APITimeoutError("timed out")
    store = make_store(tmp_path)
    request = {"marketSlug": "m", "intent": "ORDER_INTENT_BUY_LONG", "quantity": 2}
    token = store.issue("orders.create", request).token

    with pytest.raises(AmbiguousMutationError) as exc_info:
        create_order(client, request, token, store)

    assert exc_info.value.ambiguous is True
    assert exc_info.value.retry_safe is False
    assert "orders list" in exc_info.value.recovery
    assert client.orders.create_calls == [request]
