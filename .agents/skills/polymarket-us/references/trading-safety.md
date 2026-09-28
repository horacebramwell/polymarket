# Trading Safety

## Before a live action

1. Resolve the exact Polymarket US market and slug.
2. Read current BBO/book when execution price or liquidity matters.
3. Construct the exact SDK request.
4. Preview creates through the official preview endpoint; prepare other mutations against current state.
5. Present the market, intent, order type, quantity/cash amount, price or slippage, TIF, and relevant preview result.
6. Obtain explicit confirmation for that concrete pending action.
7. Execute once with the matching one-time token.
8. Report the returned result and, where useful, re-read order/position state.

A blanket statement such as “you can trade for me today” is not confirmation for a later concrete order.

## Ambiguous failures

Never blindly retry create, modify, cancel, cancel-all, or close after a timeout or connection failure. The request may have reached the exchange even when the response was lost. The CLI marks those failures `ambiguous=true` and `retrySafe=false`; inspect open orders, the specific order, and/or positions before considering a new attempt.

## Credentials and compliance

Keep `POLYMARKET_KEY_ID` and `POLYMARKET_SECRET_KEY` out of repository files and logs. Do not attempt to bypass KYC, geographic, account, market, trading-limit, or other eligibility restrictions. Surface official API rejections as returned.

## Rate limits

The official documentation currently states 20 requests/second per API key for authenticated endpoints and 20 requests/second per IP for public endpoints. Re-check current docs before designing high-frequency workflows. This skill intentionally does not implement autonomous or high-frequency trading.
