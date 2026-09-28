# Agent Installation

The canonical source is `.agents/skills/polymarket-us/`. Keep one source of truth rather than manually maintaining divergent copies.

## Codex

Project-scoped Agent Skills use `.agents/skills/`, so this repository is already laid out for Codex.

```bash
python scripts/install-skill.py --target codex
```

The command verifies availability and does not duplicate the skill.

## Google Antigravity

Project-scoped skills also use `.agents/skills/`, so the canonical directory is directly consumable.

```bash
python scripts/install-skill.py --target antigravity
```

## Claude Code

Claude Code uses `.claude/skills/` for project skills. Install a relative symlink to the canonical source:

```bash
python scripts/install-skill.py --target claude
```

If symlinks are unavailable, the installer falls back to a generated copy. It refuses to overwrite an existing independently modified destination unless `--force` is explicit.

## Hermes Agent

Prefer Hermes project-skill trust rather than silently editing user configuration:

```bash
python scripts/install-skill.py --target hermes
```

The command prints the exact `hermes skills trust <repo-root>` command. Run that command explicitly in Hermes' environment.

## All targets

```bash
python scripts/install-skill.py --target all
```

Re-run official agent documentation checks when an agent changes its discovery locations or trust model.
