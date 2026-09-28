from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest


class Recorder:
    def __init__(self, result):
        self.result = result
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.result

        return call


class FakeClient:
    def __init__(self):
        self.events = Recorder({"events": []})
        self.markets = Recorder({"marketData": {"bestBid": {"value": "0.4"}}})
        self.search = Recorder({"events": []})
        self.account = Recorder({"buyingPower": {"value": "100"}})
        self.portfolio = Recorder({"positions": []})
        self.orders = Recorder({"orders": []})


def ns(**kwargs):
    defaults = {
        "params_json": None,
        "id": None,
        "slug": None,
        "query": None,
        "order_id": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


def test_markets_search_merges_query_with_params() -> None:
    from pmus_core.read_commands import execute_read

    client = FakeClient()
    result = execute_read("markets.search", ns(query="bitcoin", params_json='{"limit": 5}'), client)

    assert result == {"events": []}
    assert client.search.calls == [("query", ({"limit": 5, "query": "bitcoin"},), {})]


def test_market_bbo_routes_to_market_resource() -> None:
    from pmus_core.read_commands import execute_read

    client = FakeClient()
    execute_read("markets.bbo", ns(slug="btc-100k"), client)

    assert client.markets.calls == [("bbo", ("btc-100k",), {})]


def test_event_get_by_id_and_slug() -> None:
    from pmus_core.read_commands import execute_read

    client = FakeClient()
    execute_read("events.get", ns(id=123), client)
    execute_read("events.get", ns(slug="super-bowl"), client)

    assert client.events.calls == [
        ("retrieve", (123,), {}),
        ("retrieve_by_slug", ("super-bowl",), {}),
    ]


def test_authenticated_read_routes() -> None:
    from pmus_core.read_commands import execute_read

    client = FakeClient()
    execute_read("account.balances", ns(), client)
    execute_read("portfolio.positions", ns(params_json='{"slugs":["x"]}'), client)
    execute_read("orders.list", ns(params_json='{"slugs":["x"]}'), client)
    execute_read("orders.get", ns(order_id="ord-1"), client)

    assert client.account.calls == [("balances", (), {})]
    assert client.portfolio.calls == [("positions", ({"slugs": ["x"]},), {})]
    assert client.orders.calls == [
        ("list", ({"slugs": ["x"]},), {}),
        ("retrieve", ("ord-1",), {}),
    ]


def test_unknown_read_command_is_rejected() -> None:
    from pmus_core.read_commands import execute_read

    with pytest.raises(ValueError, match="Unsupported read command"):
        execute_read("markets.nope", ns(), FakeClient())
