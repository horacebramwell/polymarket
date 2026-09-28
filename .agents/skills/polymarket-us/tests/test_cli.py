from __future__ import annotations

import json

import pmus


class FakeMarkets:
    def bbo(self, slug):
        return {"slug": slug, "marketData": {"bestBid": {"value": "0.51"}}}


class FakeOrders:
    def preview(self, params):
        return {"order": {"marketSlug": params["request"]["marketSlug"], "state": "ORDER_STATE_NEW"}}

    def create(self, request):
        return {"id": "ord-new", "request": request}


class FakeClient:
    def __init__(self):
        self.markets = FakeMarkets()
        self.orders = FakeOrders()
        self.closed = False

    def close(self):
        self.closed = True


class FakeIssued:
    token = "token-1"
    expires_at = 1300.0


class FakeStore:
    def issue(self, action, payload, context=None):
        assert action == "orders.create"
        return FakeIssued()

    def consume(self, token, action, payload):
        assert token == "token-1"
        assert action == "orders.create"
        return FakeIssued()


def decode_stdout(capsys):
    return json.loads(capsys.readouterr().out)


def test_cli_read_flow_emits_json(monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(pmus, "build_client", lambda authenticated: client)
    rc = pmus.main(["markets", "bbo", "demo-market"])
    payload = decode_stdout(capsys)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["command"] == "markets.bbo"
    assert payload["data"]["slug"] == "demo-market"
    assert client.closed is True


def test_cli_preview_returns_confirmation_token(monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(pmus, "build_client", lambda authenticated: client)
    monkeypatch.setattr(pmus, "ConfirmationStore", FakeStore)
    rc = pmus.main([
        "orders",
        "preview",
        "--request-json",
        '{"marketSlug":"demo","intent":"ORDER_INTENT_BUY_LONG","quantity":2}',
    ])
    payload = decode_stdout(capsys)
    assert rc == 0
    assert payload["command"] == "orders.preview"
    assert payload["data"]["confirmationToken"] == "token-1"


def test_cli_confirmed_create_uses_exact_token(monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(pmus, "build_client", lambda authenticated: client)
    monkeypatch.setattr(pmus, "ConfirmationStore", FakeStore)
    request = '{"marketSlug":"demo","intent":"ORDER_INTENT_BUY_LONG","quantity":2}'
    rc = pmus.main(["orders", "create", "--request-json", request, "--confirm", "token-1"])
    payload = decode_stdout(capsys)
    assert rc == 0
    assert payload["command"] == "orders.create"
    assert payload["data"]["id"] == "ord-new"


def test_ambiguous_error_serialization_includes_retry_safety():
    from pmus_core.client import serialize_exception
    from pmus_core.trading import AmbiguousMutationError

    payload = serialize_exception(
        "orders.create",
        AmbiguousMutationError("response lost", "Run `orders list` first."),
    )
    assert payload["error"]["ambiguous"] is True
    assert payload["error"]["retrySafe"] is False
    assert payload["error"]["recovery"] == "Run `orders list` first."
