# Polymarket US Agent Skill Design

Date: 2026-09-28
Status: Approved architecture; implementation pending plan review
Repository: `horacebramwell/polymarket`

## 1. Purpose

Build one portable Agent Skills package that lets coding agents work with the official Polymarket US developer surface safely and consistently. The skill must support market research and account inspection, and it must be capable of executing live Polymarket US trades only through an explicit preview-and-confirm workflow.

The skill is intended to work across Codex, Claude Code, Google Antigravity, Hermes Agent, and other agents that implement or can consume the open Agent Skills `SKILL.md` convention.

Success means an agent can:

- discover and inspect Polymarket US events and markets;
- search markets and inspect BBO/order-book data;
- inspect balances, positions, activity, and open orders;
- preview, create, modify, cancel, cancel-all, and close-position orders through the official Polymarket US API/SDK;
- distinguish Polymarket US from Polymarket International and never silently mix their APIs;
- refresh its API knowledge from current official Polymarket US documentation before API-sensitive work;
- keep credentials out of repository files and logs;
- require a clear user confirmation immediately before any state-changing live trade action;
- install or expose the same canonical skill to multiple agent runtimes without maintaining divergent copies.

## 2. Authoritative Sources

The implementation must treat the following sources as authoritative, in this order:

1. Polymarket US documentation index: `https://docs.polymarket.us/llms.txt`
2. Relevant pages under `https://docs.polymarket.us/`
3. Official Polymarket US Python SDK: `https://github.com/Polymarket/polymarket-us-python`
4. Official Polymarket US TypeScript SDK: `https://github.com/Polymarket/polymarket-us-typescript`

Agent-platform discovery/install behavior should be grounded in the current official docs for each platform rather than copied from stale blog posts:

- OpenAI/Codex Skills documentation under `https://developers.openai.com/`
- Claude Code Skills documentation under `https://code.claude.com/docs/en/skills`
- Google Antigravity Skills documentation/codelabs under `https://codelabs.developers.google.com/`
- Hermes Agent Skills documentation under `https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/`

The skill must prefer Polymarket US documentation over International Polymarket documentation whenever the user is asking about `polymarket.us`, US API keys, or the US SDKs.

## 3. Non-Goals for v1

The first implementation will not attempt to become a general trading bot or an autonomous strategy engine.

The following are deliberately out of scope for v1:

- autonomous trading based on signals or model judgment;
- scheduled or unattended order placement;
- automatic portfolio rebalancing;
- batch create/modify/cancel order endpoints;
- combo instrument creation;
- RFQ/quote workflows;
- long-running WebSocket daemons or background watchers;
- International Polymarket CLOB trading;
- custody, deposits, withdrawals, or movement of funds;
- bypassing eligibility, KYC, geographic, exchange, or account restrictions.

The official docs may be referenced for these surfaces, but the CLI will not expose them in the initial implementation.

## 4. Repository Layout

The repository will use one canonical project-scoped skill:

```text
.agents/skills/polymarket-us/
├── SKILL.md
├── references/
│   ├── official-sources.md
│   ├── api-workflows.md
│   ├── trading-safety.md
│   └── agent-installation.md
├── scripts/
│   ├── polymarket_us.py
│   └── check_docs.py
└── tests/
    └── test_polymarket_us.py

scripts/
└── install-skill.py

README.md
```

`SKILL.md` will be the canonical behavioral contract. Supporting material will be split into focused reference files so agents can load details progressively rather than placing the entire API manual in the initial prompt context.

The skill will not duplicate a second full `SKILL.md` under `.claude/skills`. Cross-agent support will be handled by discovery of `.agents/skills` where supported or by the installer creating an appropriate symlink/copy when required.

## 5. Cross-Agent Discovery and Installation

### Codex

The repository-scoped canonical skill lives in `.agents/skills/polymarket-us/`. Codex-compatible instructions will use the current official Codex/Agent Skills discovery behavior.

### Google Antigravity

Antigravity supports project-scoped skills in `<project-root>/.agents/skills/`, so it can consume the canonical skill directly.

### Claude Code

Claude Code discovers skills from `.claude/skills/` and user-level skill directories. The installer will expose the canonical skill to Claude Code without maintaining a manually divergent source copy. Preferred behavior is a symlink when the environment supports it; otherwise the installer may copy the directory and clearly mark the generated copy as derived from the canonical source.

### Hermes Agent

Hermes uses `~/.hermes/skills/` as its primary skill location and supports additional directories through `skills.external_dirs` in `~/.hermes/config.yaml`. Documentation will recommend pointing Hermes at the repository's `.agents/skills` directory when practical; the installer may also copy/symlink the skill into a Hermes user skill directory when explicitly requested.

### Other Agent Skills Consumers

Any runtime supporting the open Agent Skills standard can consume the canonical skill directory as long as it can discover the folder and execute its scripts.

## 6. Skill Behavior

`SKILL.md` will instruct the agent to classify a Polymarket request into one of three modes.

### Read-only mode

Examples:

- find markets about a topic;
- list active events;
- inspect a market;
- show BBO or order book;
- inspect price/market metadata;
- show balances, positions, activity, or open orders.

Read-only commands may execute without a trade confirmation.

### Trade-planning mode

Examples:

- "What would it cost to buy 50 contracts?"
- "Preview a limit order at 0.55."
- "How many contracts could I buy with $100?"

The agent may fetch current market data and call the official preview-order API, but it must not create, modify, cancel, cancel-all, or close a live order without a separate explicit confirmation of the exact state-changing action.

### Live-trade mode

For any state-changing order action, the agent must:

1. resolve the exact market slug and display the market title/context;
2. fetch current BBO/order-book data when relevant;
3. construct the exact requested order/action;
4. use the official preview endpoint where the endpoint supports previewing the intended order;
5. present a concise confirmation summary;
6. obtain explicit confirmation from the user after that summary;
7. submit the action once;
8. inspect the returned order/result and report the confirmed state;
9. if the submission result is ambiguous because of a timeout/network failure, inspect order state before considering any retry.

The confirmation summary must include, when applicable:

- market title and slug;
- intent/side semantics;
- order type;
- quantity or cash order amount;
- limit price or slippage settings;
- time in force;
- estimated notional;
- any previewed fill information returned by Polymarket US.

A general instruction such as "you can trade for me today" is not sufficient confirmation for an individual later order. Confirmation must refer to the concrete pending action.

## 7. CLI Architecture

The deterministic CLI will be implemented in Python and will use the official `polymarket-us` package.

The CLI is the execution boundary. Agents should call the CLI rather than reimplementing authentication, signatures, endpoint paths, enum values, or request shapes from memory.

Planned command surface:

```text
polymarket_us.py docs-check

polymarket_us.py events list [...filters]
polymarket_us.py events get --id <id>
polymarket_us.py events get --slug <slug>

polymarket_us.py markets list [...filters]
polymarket_us.py markets get --id <id>
polymarket_us.py markets get --slug <slug>
polymarket_us.py markets search <query>
polymarket_us.py markets bbo <slug>
polymarket_us.py markets book <slug>
polymarket_us.py markets settlement <slug>

polymarket_us.py account balances
polymarket_us.py portfolio positions [...filters]
polymarket_us.py portfolio activity [...filters]

polymarket_us.py orders list [...filters]
polymarket_us.py orders get <order-id>
polymarket_us.py orders preview <order-args>
polymarket_us.py orders create <order-args> --confirm <confirmation-token>
polymarket_us.py orders modify <order-id> <changes> --confirm <confirmation-token>
polymarket_us.py orders cancel <order-id> --market <slug> --confirm <confirmation-token>
polymarket_us.py orders cancel-all [...market filters] --confirm <confirmation-token>
polymarket_us.py positions close <slug> [...execution args] --confirm <confirmation-token>
```

Exact flags will follow the SDK request model rather than inventing an alternative vocabulary.

### Structured Output

Commands will emit machine-readable JSON by default so different agents can consume results reliably. Human-readable summaries belong in the agent layer, not in the API wrapper.

Every JSON response will use a predictable envelope:

```json
{
  "ok": true,
  "command": "markets.bbo",
  "data": {},
  "meta": {}
}
```

Errors will be normalized similarly:

```json
{
  "ok": false,
  "command": "orders.create",
  "error": {
    "type": "AuthenticationError",
    "message": "...",
    "status": 401
  }
}
```

Secrets must never be emitted in either success or error output.

## 8. Authentication and Credential Handling

The official Polymarket US SDK uses API credentials based on a key ID and Ed25519 secret key.

The CLI will read credentials only from environment variables:

```text
POLYMARKET_KEY_ID
POLYMARKET_SECRET_KEY
```

Requirements:

- never accept the secret key as a CLI argument;
- never persist credentials into repository configuration;
- never print credentials;
- never include credentials in tracebacks;
- `.env` files, if a developer chooses to use one locally, must be gitignored and must not be loaded implicitly by the production CLI unless implementation review explicitly adds that behavior;
- read-only public market commands must work without credentials;
- authenticated commands must fail clearly when credentials are unavailable.

## 9. Confirmation Mechanism

The CLI must make it difficult for an agent to accidentally bypass the user-confirmation step.

`orders preview` will produce a short-lived confirmation payload derived from the normalized request and preview context. The implementation plan will choose the simplest deterministic mechanism that does not require storing secrets, likely a hash/token over the normalized pending action plus a timestamp/expiry.

A state-changing command must receive the matching confirmation token. The CLI will reject missing, expired, or mismatched confirmation tokens before calling the SDK.

This mechanism is defense in depth. The skill instructions still require the agent to show the user the exact trade/action and obtain explicit confirmation before using the token.

For cancellations and modifications, where a create-order preview may not map exactly to the action, the CLI will generate an action-specific confirmation payload from the current order state plus requested mutation.

## 10. Documentation Freshness

`check_docs.py` will verify that official documentation remains reachable and will inspect `https://docs.polymarket.us/llms.txt` to discover current relevant pages.

The skill will instruct agents to run a docs check before:

- generating or changing API-sensitive implementation code;
- using an endpoint/field not represented in the local references;
- responding to a user who explicitly asks for the latest/current API behavior;
- diagnosing an API mismatch or unknown enum/field.

The script should not scrape the entire documentation site on every normal market lookup. It should fetch the index, identify relevant official pages, and keep the operation bounded.

Local reference files are guidance and workflow documentation, not a frozen substitute for the official docs.

## 11. Error Handling and Retry Rules

The wrapper will map official SDK exceptions into stable JSON error types.

Important behavior:

- validation/authentication/not-found errors: do not retry automatically;
- rate limits: surface retry guidance and only retry read operations conservatively;
- read-only transient failures: bounded retry with backoff is acceptable;
- state-changing trade requests: never blindly retry after an ambiguous network timeout;
- after an ambiguous create/modify/cancel response, query relevant order state first;
- malformed or unsupported enum values must fail locally when practical;
- if official docs and installed SDK appear inconsistent, stop the trade action and report the mismatch rather than guessing.

## 12. Market Semantics

The skill must explicitly teach the agent that Polymarket US order semantics are defined by official order intents and must not be reduced to vague natural-language "buy yes"/"sell no" assumptions without resolving them to the SDK/API enum.

The initial implementation must support the current official order intents exposed by the SDK, including long/short buy/sell intents, and current official order/time-in-force values.

Whole-contract, collateral, margin, trading-limit, and restriction behavior must come from current official Polymarket US documentation when relevant to a requested action.

## 13. WebSockets

The official SDK exposes authenticated WebSocket support for order, position, balance, market-data, and trade updates.

In v1:

- WebSocket capabilities will be documented in references;
- the skill may use short-lived streaming examples for debugging/development when explicitly requested;
- the primary CLI will remain request/response oriented;
- no persistent watcher or autonomous trading loop will be shipped.

A future iteration can add a dedicated stream command once the core order lifecycle is stable and tested.

## 14. Testing Strategy

Tests must not place real trades by default.

### Unit tests

Use mocks/fakes around the SDK to verify:

- argument parsing;
- normalized request construction;
- JSON output envelopes;
- error normalization;
- no credential leakage;
- confirmation-token creation and validation;
- rejection of missing/mismatched/expired confirmation;
- no state-changing SDK call occurs before confirmation validation;
- ambiguous trade failures are not blindly retried.

### Public integration tests

Optional tests may hit unauthenticated official public endpoints for:

- event listing;
- market listing/search;
- market retrieval;
- BBO/order book.

They must be skippable when network access is unavailable.

### Authenticated integration tests

Account/portfolio/order-preview integration tests are opt-in and require credentials.

Tests that can place, modify, cancel, or close live orders require an additional explicit environment opt-in such as:

```text
POLYMARKET_RUN_LIVE_TRADE_TESTS=1
```

Even with that variable set, tests must use narrowly controlled fixtures and never run as part of the default test suite.

## 15. Installer

`scripts/install-skill.py` will provide explicit installation targets rather than trying to auto-detect and mutate every agent configuration silently.

Expected modes:

```text
python scripts/install-skill.py --target claude
python scripts/install-skill.py --target hermes
python scripts/install-skill.py --target codex
python scripts/install-skill.py --target antigravity
python scripts/install-skill.py --target all
```

For Codex and Antigravity, project-local installation may be a no-op because the canonical `.agents/skills` path is already present.

For Claude and Hermes, the installer will prefer symlinks where supported and offer/perform a copy fallback. It must never overwrite an existing independently modified skill without an explicit force/update option.

## 16. README

The root README will explain:

- what the repository provides;
- that it targets Polymarket US, not International, by default;
- supported agents;
- installation commands;
- Python/SDK prerequisites;
- public vs authenticated usage;
- credential environment variables;
- example read-only workflows;
- the trade preview/confirmation flow;
- testing commands;
- safety/compliance limitations;
- links to official documentation.

## 17. Security and Compliance Boundaries

The skill is an execution interface, not a mechanism for bypassing platform rules.

It must:

- follow current Polymarket US authentication requirements;
- respect API rate limits;
- avoid credential persistence and disclosure;
- never attempt to bypass KYC, geographic, account, market, trading-limit, or other eligibility restrictions;
- surface official API rejection messages rather than disguising them;
- avoid autonomous trading or strategy execution unless a future design explicitly adds a separately reviewed mechanism;
- keep state-changing calls behind explicit confirmation.

## 18. Initial Implementation Sequence

After this design is reviewed, the implementation plan should break work into small verifiable steps:

1. repository scaffolding and dependencies;
2. canonical `SKILL.md` and reference sources;
3. read-only CLI commands;
4. authenticated account/portfolio reads;
5. order preview;
6. confirmation-token mechanism;
7. live create/modify/cancel/cancel-all/close commands;
8. installer and cross-agent docs;
9. tests and verification;
10. README and final end-to-end checks.

Implementation must follow test-driven development for behavior that can be unit tested.

## 19. Acceptance Criteria

The implementation is complete when all of the following are true:

- the canonical skill is discoverable from `.agents/skills/polymarket-us/SKILL.md`;
- `SKILL.md` uses progressive disclosure and points to focused references/scripts;
- the CLI uses the official Polymarket US Python SDK;
- public market/event/search/BBO/book commands work without credentials;
- authenticated balance/position/activity/open-order commands use environment credentials;
- preview/create/modify/cancel/cancel-all/close-position are represented in the supported workflow;
- all state-changing commands enforce CLI-level confirmation validation;
- an ambiguous state-changing request is never blindly retried;
- official docs can be checked through `llms.txt` and relevant current pages;
- the repository clearly distinguishes Polymarket US from International Polymarket APIs;
- installation guidance works for Codex, Claude Code, Antigravity, and Hermes;
- default tests cannot place a live trade;
- live-trade tests require a separate explicit opt-in;
- tests pass and no secrets are present in tracked files.
