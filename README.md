# Polymarket US Agent Skill

A portable [Agent Skills](https://agentskills.io/) package for working with the **official Polymarket US API** from Codex, Claude Code, Google Antigravity, Hermes Agent, and compatible runtimes.

It provides a deterministic Python CLI for market discovery, account/portfolio reads, order preview, and guarded live order actions. Live mutations are intentionally gated by a short-lived, one-time confirmation token bound to the exact requested action.

> This repository targets **Polymarket US** (`polymarket.us` / `docs.polymarket.us`). It does not implement the International Polymarket CLOB API.

## Requirements

- Python 3.10+
- Official `polymarket-us` Python SDK (`>=1.0.2,<2`)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Authenticated commands read credentials from environment variables only:

```bash
export POLYMARKET_KEY_ID="..."
export POLYMARKET_SECRET_KEY="..."
```

Never pass the secret key as a CLI argument or commit it to the repository.

## Install the skill for an agent

The canonical skill lives at `.agents/skills/polymarket-us/`.

```bash
python scripts/install-skill.py --target codex
python scripts/install-skill.py --target antigravity
python scripts/install-skill.py --target claude
python scripts/install-skill.py --target hermes
```

Codex and Antigravity use the canonical project path directly. Claude receives a relative `.claude/skills/polymarket-us` symlink when supported. Hermes returns an explicit `hermes skills trust <repo>` command rather than silently changing user configuration.

See `.agents/skills/polymarket-us/references/agent-installation.md` for details.

## Check current official docs

```bash
python .agents/skills/polymarket-us/scripts/check_docs.py
# or
python .agents/skills/polymarket-us/scripts/pmus.py docs-check
```

The checker reads `https://docs.polymarket.us/llms.txt` and verifies that the safety-critical pages used by this skill still exist. It does not crawl the entire documentation site.

## Read markets

```bash
PMUS="python .agents/skills/polymarket-us/scripts/pmus.py"

$PMUS events list --params-json '{"limit":10,"active":true}'
$PMUS markets search bitcoin
$PMUS markets get --slug MARKET_SLUG
$PMUS markets bbo MARKET_SLUG
$PMUS markets book MARKET_SLUG
$PMUS markets settlement MARKET_SLUG
```

All command output is JSON so coding agents can consume it reliably.

## Account and portfolio

```bash
$PMUS account balances
$PMUS portfolio positions
$PMUS portfolio activity
$PMUS orders list
$PMUS orders get ORDER_ID
```

## Preview → confirm → execute

Create orders are previewed through the official SDK first:

```bash
REQUEST='{"marketSlug":"example","intent":"ORDER_INTENT_BUY_LONG","type":"ORDER_TYPE_LIMIT","price":{"value":"0.55","currency":"USD"},"quantity":10,"tif":"TIME_IN_FORCE_GOOD_TILL_CANCEL"}'

$PMUS orders preview --request-json "$REQUEST"
```

The response includes a short-lived `confirmationToken`. An agent must show the exact concrete action to the user and receive explicit confirmation before submission. Then it executes the **same** request with that token:

```bash
$PMUS orders create --request-json "$REQUEST" --confirm TOKEN
```

Changing the request invalidates the token, and a successful token consumption is one-time.

Other state changes use the same two-stage model:

```bash
$PMUS orders prepare-modify ORDER_ID --request-json '{...}'
$PMUS orders modify ORDER_ID --request-json '{...}' --confirm TOKEN

$PMUS orders prepare-cancel ORDER_ID --market MARKET_SLUG
$PMUS orders cancel ORDER_ID --market MARKET_SLUG --confirm TOKEN

$PMUS orders prepare-cancel-all --slugs MARKET_A MARKET_B
$PMUS orders cancel-all --slugs MARKET_A MARKET_B --confirm TOKEN

$PMUS positions prepare-close --request-json '{"marketSlug":"MARKET_SLUG"}'
$PMUS positions close --request-json '{"marketSlug":"MARKET_SLUG"}' --confirm TOKEN
```

### Ambiguous network failures

State-changing calls are never automatically retried after timeout/connection ambiguity. The CLI returns `ambiguous: true`, `retrySafe: false`, and a recovery hint. Inspect the current order/position state before considering another action.

## Tests

```bash
pytest -q
ruff check .
```

The default suite never places a real trade. Unit tests use fake SDK clients. The docs checker is the only final verification step that requires public network access.

## v1 boundaries

This repository deliberately does **not** implement autonomous trading, scheduled/unattended order placement, batch order APIs, combos/RFQs, persistent WebSocket daemons, deposits/withdrawals, restriction bypasses, or International Polymarket trading.

WebSocket capabilities are documented by Polymarket US and can be added later as a separately reviewed feature once the core order lifecycle is stable.

## Official sources

- https://docs.polymarket.us/llms.txt
- https://docs.polymarket.us/
- https://github.com/Polymarket/polymarket-us-python
- https://github.com/Polymarket/polymarket-us-typescript

See `.agents/skills/polymarket-us/references/official-sources.md` for source precedence and the current preview-shape compatibility note.
