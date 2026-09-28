from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class ConfirmationError(RuntimeError):
    """Raised when a confirmation token cannot authorize the requested action."""


@dataclass(frozen=True)
class ConfirmationRecord:
    token: str
    action: str
    expires_at: float
    context: dict[str, object]


def canonical_payload(action: str, payload: dict[str, object]) -> bytes:
    return json.dumps(
        {"action": action, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(action: str, payload: dict[str, object]) -> str:
    return hashlib.sha256(canonical_payload(action, payload)).hexdigest()


class ConfirmationStore:
    def __init__(
        self,
        root: Path | None = None,
        ttl_seconds: int = 300,
        clock: Callable[[], float] = time.time,
    ) -> None:
        default_root = Path.home() / ".cache" / "polymarket-us-skill" / "confirmations"
        self.root = Path(root or os.environ.get("POLYMARKET_CONFIRMATION_DIR", default_root))
        self.ttl_seconds = ttl_seconds
        self.clock = clock

    def _ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _path(self, token: str) -> Path:
        return self.root / f"{self._token_hash(token)}.json"

    def issue(
        self,
        action: str,
        payload: dict[str, object],
        context: dict[str, object] | None = None,
    ) -> ConfirmationRecord:
        self._ensure_root()
        token = secrets.token_urlsafe(24)
        now = self.clock()
        expires_at = now + self.ttl_seconds
        record = {
            "action": action,
            "payloadDigest": _digest(action, payload),
            "createdAt": now,
            "expiresAt": expires_at,
            "context": context or {},
        }
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        path = self._path(token)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return ConfirmationRecord(token=token, action=action, expires_at=expires_at, context=context or {})

    def consume(
        self,
        token: str,
        action: str,
        payload: dict[str, object],
    ) -> ConfirmationRecord:
        self._ensure_root()
        path = self._path(token)
        if not path.exists():
            raise ConfirmationError("Confirmation token not found or already consumed")
        try:
            record = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfirmationError("Confirmation token record is unreadable") from exc

        if self.clock() > float(record["expiresAt"]):
            path.unlink(missing_ok=True)
            raise ConfirmationError("Confirmation token expired")
        expected = _digest(action, payload)
        if record.get("action") != action or record.get("payloadDigest") != expected:
            raise ConfirmationError("Confirmation token does not match the requested action")

        consumed = path.with_suffix(f".{secrets.token_hex(6)}.consumed")
        try:
            os.replace(path, consumed)
        except FileNotFoundError as exc:
            raise ConfirmationError("Confirmation token not found or already consumed") from exc
        try:
            context = record.get("context") or {}
            return ConfirmationRecord(
                token=token,
                action=action,
                expires_at=float(record["expiresAt"]),
                context=context,
            )
        finally:
            consumed.unlink(missing_ok=True)
