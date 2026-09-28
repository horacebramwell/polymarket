from __future__ import annotations

import sys
import types

import pytest


def test_parse_json_object_rejects_non_object() -> None:
    from pmus_core.client import parse_json_object

    with pytest.raises(ValueError, match="params-json must be a JSON object"):
        parse_json_object("[1, 2]", "params-json")


def test_success_envelope() -> None:
    from pmus_core.output import success

    assert success("markets.bbo", {"bestBid": "0.42"}) == {
        "ok": True,
        "command": "markets.bbo",
        "data": {"bestBid": "0.42"},
        "meta": {},
    }


def test_failure_envelope() -> None:
    from pmus_core.output import failure

    assert failure("orders.create", "BadRequestError", "bad input", status=400) == {
        "ok": False,
        "command": "orders.create",
        "error": {
            "type": "BadRequestError",
            "message": "bad input",
            "status": 400,
        },
    }


def test_authenticated_client_requires_environment_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from pmus_core.client import CredentialError, build_client

    fake_sdk = types.ModuleType("polymarket_us")
    fake_sdk.PolymarketUS = object
    monkeypatch.setitem(sys.modules, "polymarket_us", fake_sdk)
    monkeypatch.delenv("POLYMARKET_KEY_ID", raising=False)
    monkeypatch.delenv("POLYMARKET_SECRET_KEY", raising=False)

    with pytest.raises(CredentialError, match="POLYMARKET_KEY_ID"):
        build_client(authenticated=True)
