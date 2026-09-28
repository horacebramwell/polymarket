from __future__ import annotations

import pytest


def test_confirmation_token_is_one_time_and_not_persisted_raw(tmp_path) -> None:
    from pmus_core.confirmation import ConfirmationError, ConfirmationStore

    store = ConfirmationStore(root=tmp_path, ttl_seconds=300, clock=lambda: 1000.0)
    issued = store.issue("orders.create", {"marketSlug": "m", "quantity": 2})

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert issued.token not in files[0].read_text()

    consumed = store.consume(
        issued.token,
        "orders.create",
        {"marketSlug": "m", "quantity": 2},
    )
    assert consumed.action == "orders.create"

    with pytest.raises(ConfirmationError, match="not found|already consumed"):
        store.consume(issued.token, "orders.create", {"marketSlug": "m", "quantity": 2})


def test_confirmation_rejects_expired_token(tmp_path) -> None:
    from pmus_core.confirmation import ConfirmationError, ConfirmationStore

    now = [1000.0]
    store = ConfirmationStore(root=tmp_path, ttl_seconds=10, clock=lambda: now[0])
    issued = store.issue("orders.create", {"marketSlug": "m"})
    now[0] = 1011.0

    with pytest.raises(ConfirmationError, match="expired"):
        store.consume(issued.token, "orders.create", {"marketSlug": "m"})


def test_confirmation_rejects_action_or_payload_mismatch(tmp_path) -> None:
    from pmus_core.confirmation import ConfirmationError, ConfirmationStore

    store = ConfirmationStore(root=tmp_path, ttl_seconds=300, clock=lambda: 1000.0)
    issued = store.issue("orders.create", {"marketSlug": "m", "quantity": 2})

    with pytest.raises(ConfirmationError, match="does not match"):
        store.consume(issued.token, "orders.cancel", {"marketSlug": "m", "quantity": 2})

    with pytest.raises(ConfirmationError, match="does not match"):
        store.consume(issued.token, "orders.create", {"marketSlug": "m", "quantity": 3})

    # A mismatch attempt must not burn the valid token.
    consumed = store.consume(
        issued.token,
        "orders.create",
        {"marketSlug": "m", "quantity": 2},
    )
    assert consumed.action == "orders.create"
