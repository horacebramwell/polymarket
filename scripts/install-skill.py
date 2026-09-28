#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import NamedTuple


class InstallError(RuntimeError):
    pass


class InstallResult(NamedTuple):
    target: str
    status: str
    path: Path
    command: str | None = None
    message: str | None = None


def _canonical(repo_root: Path) -> Path:
    skill = repo_root.resolve() / ".agents" / "skills" / "polymarket-us"
    if not (skill / "SKILL.md").is_file():
        raise InstallError(f"Canonical skill not found at {skill}")
    return skill


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _install_claude(repo_root: Path, canonical: Path, force: bool) -> InstallResult:
    destination = repo_root / ".claude" / "skills" / "polymarket-us"
    relative = Path(os.path.relpath(canonical, destination.parent))
    if destination.is_symlink() and destination.readlink() == relative:
        return InstallResult("claude", "already-linked", destination)
    if destination.exists() or destination.is_symlink():
        if not force:
            raise InstallError(f"Claude skill path already exists: {destination}; use --force to replace it")
        _remove_existing(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.symlink_to(relative, target_is_directory=True)
        return InstallResult("claude", "linked", destination)
    except OSError:
        shutil.copytree(canonical, destination)
        return InstallResult(
            "claude",
            "copied",
            destination,
            message="Symlinks are unavailable; copied from the canonical skill.",
        )


def install(repo_root: Path, target: str, force: bool = False) -> InstallResult:
    repo_root = repo_root.resolve()
    canonical = _canonical(repo_root)
    if target in {"codex", "antigravity"}:
        return InstallResult(target, "available", canonical)
    if target == "claude":
        return _install_claude(repo_root, canonical, force)
    if target == "hermes":
        return InstallResult(
            "hermes",
            "trust-required",
            canonical,
            command=f"hermes skills trust {repo_root}",
            message="Trust this repository so Hermes can discover its project skill.",
        )
    raise InstallError(f"Unsupported target: {target}")


def _as_json(result: InstallResult) -> dict[str, object]:
    return {
        "target": result.target,
        "status": result.status,
        "path": str(result.path),
        "command": result.command,
        "message": result.message,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expose the canonical Polymarket US skill to agent runtimes.")
    parser.add_argument("--target", required=True, choices=("codex", "claude", "antigravity", "hermes", "all"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    targets = ("codex", "claude", "antigravity", "hermes") if args.target == "all" else (args.target,)
    try:
        results = [install(args.repo_root, target, args.force) for target in targets]
    except InstallError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 1
    print(json.dumps({"ok": True, "results": [_as_json(result) for result in results]}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
