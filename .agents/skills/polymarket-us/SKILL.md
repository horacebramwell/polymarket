---
name: polymarket-us
description: Use for Polymarket US developer/API work, finding or inspecting US events and markets, order books/BBO, account balances, positions, activity, order previews, or user-requested live order create/modify/cancel/close actions. Use only the official Polymarket US docs/SDK; do not substitute International Polymarket CLOB APIs.
---

# Polymarket US

Use this skill for **Polymarket US** (`polymarket.us` / `docs.polymarket.us`). If the user explicitly means International Polymarket, stop using this skill rather than mixing APIs.

## Execution boundary

Use `scripts/pmus.py` from this skill for API operations. Do not hand-roll Ed25519 signatures, endpoint paths, enum names, or live request shapes when the CLI covers the operation.

Read `references/official-sources.md` when API freshness matters. Run `scripts/check_docs.py` before changing API-sensitive code, using an unfamiliar field/endpoint, diagnosing schema drift, or answering a request that explicitly asks for current API behavior.

Read `references/api-workflows.md` for commands and current SDK vocabulary. Read `references/trading-safety.md` before any live mutation.

## Request modes

### Read only

Market/event discovery, search, BBO/book/settlement, balances, positions, activity, and open-order inspection may run without trade confirmation. Authenticated reads still require environment credentials.

### Plan or preview

For “what would this cost?”, “preview this order”, or similar requests, fetch current market data as relevant and use the official preview flow. Previewing does not authorize submission.

### Live mutation

For create, modify, cancel, cancel-all, or close-position:

1. Resolve the exact market/order and inspect current state.
2. Use `orders preview` for creates or the matching `prepare-*` command for other mutations.
3. Present the exact concrete action: market, intent, type, quantity/cash amount, price/slippage, TIF, and preview/current-state details as applicable.
4. Obtain explicit user confirmation **after** presenting that action.
5. Execute the exact same action once with the returned one-time confirmation token.
6. Report the API result and verify state when useful.

Never treat blanket standing permission as confirmation for a later concrete trade. Never bypass the CLI token by calling the SDK directly.

## Ambiguous mutation failures

Do not blindly retry a state-changing call after a timeout or connection failure. The request may have reached the exchange. Follow the CLI recovery hint and inspect order/position state before considering another action.

## Credentials and restrictions

Read credentials only from `POLYMARKET_KEY_ID` and `POLYMARKET_SECRET_KEY`. Never request that the secret be placed in a CLI argument or committed file, and never print it.

Do not bypass KYC, geography, account eligibility, trading limits, market restrictions, or exchange controls. Surface official rejection messages.

## Scope

This v1 skill does not automate strategies, schedule unattended trades, implement batch order endpoints, combos/RFQs, persistent WebSocket watchers, deposits/withdrawals, or International Polymarket trading.
