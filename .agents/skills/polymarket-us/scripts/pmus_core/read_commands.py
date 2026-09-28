from __future__ import annotations

from argparse import Namespace

from .client import parse_json_object


def _params(args: Namespace) -> dict[str, object]:
    return parse_json_object(getattr(args, "params_json", None), "params-json")


def execute_read(command: str, args: Namespace, client: object) -> object:
    if command == "events.list":
        params = _params(args)
        return client.events.list(params or None)
    if command == "events.get":
        if getattr(args, "id", None) is not None:
            return client.events.retrieve(args.id)
        return client.events.retrieve_by_slug(args.slug)

    if command == "markets.list":
        params = _params(args)
        return client.markets.list(params or None)
    if command == "markets.get":
        if getattr(args, "id", None) is not None:
            return client.markets.retrieve(args.id)
        return client.markets.retrieve_by_slug(args.slug)
    if command == "markets.search":
        params = _params(args)
        params["query"] = args.query
        return client.search.query(params)
    if command == "markets.bbo":
        return client.markets.bbo(args.slug)
    if command == "markets.book":
        return client.markets.book(args.slug)
    if command == "markets.settlement":
        return client.markets.settlement(args.slug)

    if command == "account.balances":
        return client.account.balances()
    if command == "portfolio.positions":
        params = _params(args)
        return client.portfolio.positions(params or None)
    if command == "portfolio.activity":
        params = _params(args)
        return client.portfolio.activities(params or None)
    if command == "orders.list":
        params = _params(args)
        return client.orders.list(params or None)
    if command == "orders.get":
        return client.orders.retrieve(args.order_id)

    raise ValueError(f"Unsupported read command: {command}")
