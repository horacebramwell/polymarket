# Official Sources

Use these sources in this order for Polymarket US work:

1. `https://docs.polymarket.us/llms.txt` — current documentation index.
2. The relevant page under `https://docs.polymarket.us/`.
3. `https://github.com/Polymarket/polymarket-us-python` — authoritative current Python SDK behavior.
4. `https://github.com/Polymarket/polymarket-us-typescript` — secondary SDK cross-check.

Do not substitute the International Polymarket CLOB/Gamma APIs for Polymarket US. The US API uses its own hosts, credentials, request shapes, and SDKs.

## Freshness rule

Run `python .agents/skills/polymarket-us/scripts/check_docs.py` before changing API-sensitive code, using an unfamiliar endpoint/field, diagnosing a schema mismatch, or answering a request that explicitly asks for current API behavior.

The local references explain workflow; they are not a frozen API manual.

## Known SDK/docs discrepancy

As checked on 2026-09-28, the current Python SDK source defines `orders.preview()` to receive `PreviewOrderParams`, whose shape is `{"request": CreateOrderParams}`. Some generated SDK documentation examples show the order fields passed directly. The CLI deliberately isolates this behind its preview adapter and tests the current SDK-source contract. Re-check the official source before changing that adapter.

## Credentials

Polymarket US authenticated endpoints use a key ID and Ed25519 secret key. This repository expects only:

- `POLYMARKET_KEY_ID`
- `POLYMARKET_SECRET_KEY`

Never paste the secret into a command-line flag, source file, issue, log, or chat transcript.
