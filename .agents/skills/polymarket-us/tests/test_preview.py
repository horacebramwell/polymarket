from __future__ import annotations


class FakeOrders:
    def __init__(self) -> None:
        self.calls = []

    def preview(self, params):
        self.calls.append(params)
        return {"order": {"marketSlug": params["request"]["marketSlug"], "state": "ORDER_STATE_NEW"}}


class FakeClient:
    def __init__(self) -> None:
        self.orders = FakeOrders()


def test_preview_uses_current_sdk_request_wrapper_and_issues_token(tmp_path) -> None:
    from pmus_core.confirmation import ConfirmationStore
    from pmus_core.trading import preview_create

    client = FakeClient()
    store = ConfirmationStore(root=tmp_path, ttl_seconds=300, clock=lambda: 1000.0)
    request = {
        "marketSlug": "btc-100k",
        "intent": "ORDER_INTENT_BUY_LONG",
        "type": "ORDER_TYPE_LIMIT",
        "price": {"value": "0.55", "currency": "USD"},
        "quantity": 2,
    }

    result = preview_create(client, request, store)

    assert client.orders.calls == [{"request": request}]
    assert result["preview"]["order"]["marketSlug"] == "btc-100k"
    assert result["normalizedRequest"] == request
    assert result["confirmationToken"]
    assert result["expiresAt"] == 1300.0

    consumed = store.consume(result["confirmationToken"], "orders.create", request)
    assert consumed.context["preview"]["order"]["state"] == "ORDER_STATE_NEW"
