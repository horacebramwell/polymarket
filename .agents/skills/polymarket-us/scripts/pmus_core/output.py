from __future__ import annotations

from typing import Any


def success(command: str, data: object, meta: dict[str, object] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "data": data,
        "meta": meta or {},
    }


def failure(command: str, error_type: str, message: str, **meta: object) -> dict[str, Any]:
    error: dict[str, object] = {"type": error_type, "message": message}
    error.update({key: value for key, value in meta.items() if value is not None})
    return {
        "ok": False,
        "command": command,
        "error": error,
    }
