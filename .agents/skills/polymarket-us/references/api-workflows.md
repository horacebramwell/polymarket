# API Workflows

The CLI is the execution boundary. Prefer it over handwritten HTTP or reimplementing SDK authentication.

Set a helper while working from the repository root:

```bash
PMUS="python .agents/skills/polymarket-us/scripts/pmus.py"
```

## Public discovery

```bash
$PMUS events list --params-json '{"limit":10,"active":true}'
$PMUS markets search bitcoin
$PMUS markets get --slug btc-example
$PMUS markets bbo btc-example
$PMUS markets book btc-example
```

## Authenticated reads

```bash
$PMUS account balances
$PMUS portfolio positions
$PMUS portfolio activity
$PMUS orders list
$PMUS orders get ORDER_ID
```

## Create-order flow

Preview first:

```bash
$PMUS orders preview --request-json '{
  "marketSlug":"example",
  "intent":"ORDER_INTENT_BUY_LONG",
  "type":"ORDER_TYPE_LIMIT",
  "price":{"value":"0.55","currency":"USD"},
  "quantity":10,
  "tif":"TIME_IN_FORCE_GOOD_TILL_CANCEL"
}'
```

Show the returned market/order details and exact action to the user. After explicit confirmation, execute the exact same request with the returned one-time token:

```bash
$PMUS orders create --request-json '<same JSON>' --confirm '<token>'
```

Any field change invalidates the token. A consumed token cannot be reused.

## Other mutations

Use prepare then execute:

```text
orders prepare-modify -> orders modify
orders prepare-cancel -> orders cancel
orders prepare-cancel-all -> orders cancel-all
positions prepare-close -> positions close
```

Prepare commands fetch relevant current state and return a short-lived token. The execution command must repeat the exact action parameters so the token can bind to them.

## Order vocabulary

Use the official SDK enum values, not ambiguous shorthand. Current order intents include:

- `ORDER_INTENT_BUY_LONG`
- `ORDER_INTENT_SELL_LONG`
- `ORDER_INTENT_BUY_SHORT`
- `ORDER_INTENT_SELL_SHORT`

Current time-in-force values include GTC, GTD, IOC, and FOK enum names from the SDK. Re-check official docs/source when the user asks for current behavior.
