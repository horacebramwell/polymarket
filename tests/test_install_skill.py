from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "install-skill.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("install_skill", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    skill = repo / ".agents" / "skills" / "polymarket-us"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: polymarket-us\n---\n", encoding="utf-8")
    return repo


def test_codex_and_antigravity_use_canonical_skill_without_copy(tmp_path):
    module = load_installer()
    repo = make_repo(tmp_path)
    for target in ("codex", "antigravity"):
        result = module.install(repo, target)
        assert result.status == "available"
        assert result.path == repo / ".agents" / "skills" / "polymarket-us"
    assert not (repo / ".claude").exists()


def test_claude_install_creates_relative_symlink(tmp_path):
    module = load_installer()
    repo = make_repo(tmp_path)
    result = module.install(repo, "claude")
    destination = repo / ".claude" / "skills" / "polymarket-us"
    assert result.status == "linked"
    assert destination.is_symlink()
    assert destination.readlink() == Path("../../.agents/skills/polymarket-us")


def test_claude_collision_refuses_without_force(tmp_path):
    module = load_installer()
    repo = make_repo(tmp_path)
    destination = repo / ".claude" / "skills" / "polymarket-us"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text("independent", encoding="utf-8")
    with pytest.raises(module.InstallError, match="already exists"):
        module.install(repo, "claude")
    assert (destination / "SKILL.md").read_text(encoding="utf-8") == "independent"


def test_hermes_returns_explicit_trust_command_without_mutating_home(tmp_path):
    module = load_installer()
    repo = make_repo(tmp_path)
    result = module.install(repo, "hermes")
    assert result.status == "trust-required"
    assert result.command == f"hermes skills trust {repo}"
