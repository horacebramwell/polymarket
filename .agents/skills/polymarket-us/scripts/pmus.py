#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pmus_core.client import build_client, parse_json_object, serialize_exception
from pmus_core.confirmation import ConfirmationStore
from pmus_core.docs_check import check_required_docs
from pmus_core.output import success
from pmus_core.read_commands import execute_read
from pmus_core.trading import (
    cancel_all_orders,
    cancel_order,
    close_position,
    create_order,
    modify_order,
    prepare_cancel,
    prepare_cancel_all,
    prepare_close_position,
    prepare_modify,
    preview_create,
)

AUTHENTICATED_COMMANDS = {
    "account.balances",
    "portfolio.positions",
    "portfolio.activity",
    "orders.list",
    "orders.get",
    "orders.preview",
    "orders.create",
    "orders.prepare-modify",
    "orders.modify",
    "orders.prepare-cancel",
    "orders.cancel",
    "orders.prepare-cancel-all",
    "orders.cancel-all",
    "positions.prepare-close",
    "positions.close",
}
TRADING_COMMANDS = {
    "orders.preview",
    "orders.create",
    "orders.prepare-modify",
    "orders.modify",
    "orders.prepare-cancel",
    "orders.cancel",
    "orders.prepare-cancel-all",
    "orders.cancel-all",
    "positions.prepare-close",
    "positions.close",
}


def _params_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--params-json", help="Optional SDK parameter object as JSON")


def _request_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-json", required=True, help="Exact SDK request object as JSON")


def _confirm_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--confirm", required=True, help="One-time token from preview/prepare")


def _slug_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("slug")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pmus.py",
        description="Guarded CLI for the official Polymarket US API.",
    )
    root = parser.add_subparsers(dest="group")

    docs = root.add_parser("docs-check")
    docs.set_defaults(command="docs-check")

    events = root.add_parser("events")
    events_sub = events.add_subparsers(dest="action")
    events_list = events_sub.add_parser("list")
    _params_arg(events_list)
    events_list.set_defaults(command="events.list")
    events_get = events_sub.add_parser("get")
    event_key = events_get.add_mutually_exclusive_group(required=True)
    event_key.add_argument("--id", type=int)
    event_key.add_argument("--slug")
    events_get.set_defaults(command="events.get")

    markets = root.add_parser("markets")
    markets_sub = markets.add_subparsers(dest="action")
    markets_list = markets_sub.add_parser("list")
    _params_arg(markets_list)
    markets_list.set_defaults(command="markets.list")
    markets_get = markets_sub.add_parser("get")
    market_key = markets_get.add_mutually_exclusive_group(required=True)
    market_key.add_argument("--id", type=int)
    market_key.add_argument("--slug")
    markets_get.set_defaults(command="markets.get")
    markets_search = markets_sub.add_parser("search")
    markets_search.add_argument("query")
    _params_arg(markets_search)
    markets_search.set_defaults(command="markets.search")
    for action in ("bbo", "book", "settlement"):
        sub = markets_sub.add_parser(action)
        _slug_arg(sub)
        sub.set_defaults(command=f"markets.{action}")

    account = root.add_parser("account")
    account_sub = account.add_subparsers(dest="action")
    balances = account_sub.add_parser("balances")
    balances.set_defaults(command="account.balances")

    portfolio = root.add_parser("portfolio")
    portfolio_sub = portfolio.add_subparsers(dest="action")
    for action in ("positions", "activity"):
        sub = portfolio_sub.add_parser(action)
        _params_arg(sub)
        sub.set_defaults(command=f"portfolio.{action}")

    orders = root.add_parser("orders")
    orders_sub = orders.add_subparsers(dest="action")
    orders_list = orders_sub.add_parser("list")
    _params_arg(orders_list)
    orders_list.set_defaults(command="orders.list")
    orders_get = orders_sub.add_parser("get")
    orders_get.add_argument("order_id")
    orders_get.set_defaults(command="orders.get")

    preview = orders_sub.add_parser("preview")
    _request_arg(preview)
    preview.set_defaults(command="orders.preview")
    create = orders_sub.add_parser("create")
    _request_arg(create)
    _confirm_arg(create)
    create.set_defaults(command="orders.create")

    prepare_modify_cmd = orders_sub.add_parser("prepare-modify")
    prepare_modify_cmd.add_argument("order_id")
    _request_arg(prepare_modify_cmd)
    prepare_modify_cmd.set_defaults(command="orders.prepare-modify")
    modify = orders_sub.add_parser("modify")
    modify.add_argument("order_id")
    _request_arg(modify)
    _confirm_arg(modify)
    modify.set_defaults(command="orders.modify")

    prepare_cancel_cmd = orders_sub.add_parser("prepare-cancel")
    prepare_cancel_cmd.add_argument("order_id")
    prepare_cancel_cmd.add_argument("--market", required=True)
    prepare_cancel_cmd.set_defaults(command="orders.prepare-cancel")
    cancel = orders_sub.add_parser("cancel")
    cancel.add_argument("order_id")
    cancel.add_argument("--market", required=True)
    _confirm_arg(cancel)
    cancel.set_defaults(command="orders.cancel")

    prepare_cancel_all_cmd = orders_sub.add_parser("prepare-cancel-all")
    prepare_cancel_all_cmd.add_argument("--slugs", nargs="*")
    prepare_cancel_all_cmd.set_defaults(command="orders.prepare-cancel-all")
    cancel_all = orders_sub.add_parser("cancel-all")
    cancel_all.add_argument("--slugs", nargs="*")
    _confirm_arg(cancel_all)
    cancel_all.set_defaults(command="orders.cancel-all")

    positions = root.add_parser("positions")
    positions_sub = positions.add_subparsers(dest="action")
    prepare_close = positions_sub.add_parser("prepare-close")
    _request_arg(prepare_close)
    prepare_close.set_defaults(command="positions.prepare-close")
    close = positions_sub.add_parser("close")
    _request_arg(close)
    _confirm_arg(close)
    close.set_defaults(command="positions.close")

    return parser


def _close(client: object) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()


def _emit(payload: object) -> None:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str))


def _execute_trading(command: str, args: argparse.Namespace, client: object) -> object:
    store = ConfirmationStore()
    if command == "orders.preview":
        return preview_create(client, parse_json_object(args.request_json, "request-json"), store)
    if command == "orders.create":
        return create_order(
            client,
            parse_json_object(args.request_json, "request-json"),
            args.confirm,
            store,
        )
    if command == "orders.prepare-modify":
        return prepare_modify(
            client,
            args.order_id,
            parse_json_object(args.request_json, "request-json"),
            store,
        )
    if command == "orders.modify":
        return modify_order(
            client,
            args.order_id,
            parse_json_object(args.request_json, "request-json"),
            args.confirm,
            store,
        )
    if command == "orders.prepare-cancel":
        return prepare_cancel(client, args.order_id, args.market, store)
    if command == "orders.cancel":
        return cancel_order(client, args.order_id, args.market, args.confirm, store)
    if command == "orders.prepare-cancel-all":
        return prepare_cancel_all(client, args.slugs, store)
    if command == "orders.cancel-all":
        return cancel_all_orders(client, args.slugs, args.confirm, store)
    if command == "positions.prepare-close":
        return prepare_close_position(
            client,
            parse_json_object(args.request_json, "request-json"),
            store,
        )
    if command == "positions.close":
        return close_position(
            client,
            parse_json_object(args.request_json, "request-json"),
            args.confirm,
            store,
        )
    raise ValueError(f"Unsupported trading command: {command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    if command == "docs-check":
        try:
            result = check_required_docs()
            _emit(success(command, result))
            return 0 if result["ok"] else 1
        except Exception as exc:
            _emit(serialize_exception(command, exc))
            return 1

    client = None
    try:
        client = build_client(authenticated=command in AUTHENTICATED_COMMANDS)
        if command in TRADING_COMMANDS:
            data = _execute_trading(command, args, client)
        else:
            data = execute_read(command, args, client)
        _emit(success(command, data))
        return 0
    except Exception as exc:
        _emit(serialize_exception(command, exc))
        return 1
    finally:
        if client is not None:
            _close(client)


if __name__ == "__main__":
    raise SystemExit(main())
