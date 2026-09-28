from __future__ import annotations

import json
import os
from typing import Any

from .output import failure


class CredentialError(RuntimeError):
    """Raised when authenticated commands lack required environment credentials."""


def parse_json_object(raw: str | None, field_name: str) -> dict[str, object]:
    if raw is None or raw == "":
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return parsed


def build_client(authenticated: bool) -> object:
    from polymarket_us import PolymarketUS

    if not authenticated:
        return PolymarketUS()

    key_id = os.environ.get("POLYMARKET_KEY_ID")
    secret_key = os.environ.get("POLYMARKET_SECRET_KEY")
    missing = [
        name
        for name, value in (
            ("POLYMARKET_KEY_ID", key_id),
            ("POLYMARKET_SECRET_KEY", secret_key),
        )
        if not value
    ]
    if missing:
        raise CredentialError(
            "Missing required environment credential(s): " + ", ".join(missing)
        )
    return PolymarketUS(key_id=key_id, secret_key=secret_key)


def serialize_exception(command: str, exc: Exception) -> dict[str, Any]:
    message = getattr(exc, "message", None) or str(exc) or exc.__class__.__name__
    status = getattr(exc, "status", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    metadata: dict[str, Any] = {"status": status}
    if hasattr(exc, "ambiguous"):
        metadata["ambiguous"] = bool(exc.ambiguous)
    if hasattr(exc, "retry_safe"):
        metadata["retrySafe"] = bool(exc.retry_safe)
    if hasattr(exc, "recovery"):
        metadata["recovery"] = str(exc.recovery)
    return failure(command, exc.__class__.__name__, message, **metadata)
