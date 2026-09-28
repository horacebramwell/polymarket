# Polymarket US Agent Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable Agent Skills package that uses the official Polymarket US Python SDK for market/account reads and guarded live order actions across Codex, Claude Code, Antigravity, and Hermes.

**Architecture:** One canonical skill lives at `.agents/skills/polymarket-us/`. A deterministic Python CLI wraps the official `polymarket-us` SDK and emits JSON; state-changing actions require a short-lived one-time confirmation token bound to the exact normalized action. The skill and references teach agents when to refresh official docs, how to invoke the CLI, and how to expose the same canonical skill to runtimes that use different discovery paths.

**Tech Stack:** Python 3.10+, `polymarket-us>=1.0.2,<2`, stdlib `argparse`/`json`/`urllib`, pytest, ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-28-polymarket-us-agent-skill-design.md`

## Global Constraints

- Target Polymarket US only; never silently substitute International Polymarket CLOB APIs.
- Treat `https://docs.polymarket.us/llms.txt`, current Polymarket US docs, and official SDK source as authoritative.
- Public market commands work without credentials; authenticated commands read only `POLYMARKET_KEY_ID` and `POLYMARKET_SECRET_KEY` from the environment.
- Never print, persist, or accept the secret key as a CLI argument.
- Every live create/modify/cancel/cancel-all/close action requires a concrete user confirmation represented by a short-lived one-time CLI token.
- Never blindly retry a state-changing request after timeout or connection ambiguity.
- Default output is machine-readable JSON with stable success/error envelopes.
- Batch orders, combos, RFQs, autonomous trading, background watchers, deposits/withdrawals, and International Polymarket are out of scope.
- Ruling: use `scripts/pmus.py`, not `scripts/polymarket_us.py`; the spec's planned filename would shadow the installed `polymarket_us` SDK module when executed from the same directory.

## Review Focus

- Malformed or non-object JSON input must fail locally with a structured error before any SDK call; Task 1 tests this.
- SDK/documentation drift around `orders.preview()` must be isolated behind one adapter and pinned by a contract test; Task 3 tests the current `{"request": create_order}` SDK shape.
- Missing, expired, reused, or payload-mismatched confirmation tokens must prevent all state-changing SDK calls; Task 3 tests each case.
- Timeout/connection failures during mutations must be reported as ambiguous and never retried automatically; Task 4 tests this behavior.
- Installer targets must never overwrite an independently modified existing skill path without `--force`; Task 6 tests collisions and symlink behavior.

---

### Task 1: Project scaffold, JSON contract, and SDK client boundary

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.agents/skills/polymarket-us/scripts/pmus.py`
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/__init__.py`
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/output.py`
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/client.py`
- Create: `.agents/skills/polymarket-us/tests/conftest.py`
- Create: `.agents/skills/polymarket-us/tests/test_core.py`

**Interfaces:**
- Produces: `parse_json_object(raw: str | None, field_name: str) -> dict[str, object]`; `success(command: str, data: object, meta: dict[str, object] | None = None) -> dict`; `failure(command: str, error_type: str, message: str, **meta: object) -> dict`; `build_client(authenticated: bool) -> object`; `serialize_exception(command: str, exc: Exception) -> dict`.
- Produces CLI entrypoint `main(argv: list[str] | None = None) -> int` in `pmus.py`.

- [ ] **Step 1: Write failing tests for JSON parsing and stable output envelopes**

Tests: `test_parse_json_object_rejects_non_object`, `test_success_envelope`, `test_failure_envelope`, `test_authenticated_client_requires_environment_credentials`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_core.py -q`
Expected: FAIL because `pmus_core` does not exist.

- [ ] **Step 3: Implement the minimal scaffold and client boundary**

`build_client(False)` constructs `PolymarketUS()`; `build_client(True)` reads the two credential environment variables and constructs `PolymarketUS(key_id=..., secret_key=...)`. `parse_json_object` accepts omitted input as `{}` and rejects invalid JSON/non-object JSON.

- [ ] **Step 4: Run focused tests and full suite**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_core.py -q`
Expected: PASS.

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "feat: scaffold Polymarket US skill CLI"`

### Task 2: Read-only market, event, search, account, and portfolio commands

**Files:**
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/read_commands.py`
- Modify: `.agents/skills/polymarket-us/scripts/pmus.py`
- Create: `.agents/skills/polymarket-us/tests/test_read_commands.py`

**Interfaces:**
- Consumes: `build_client`, `parse_json_object`, output envelope helpers.
- Produces: `execute_read(command: str, args: argparse.Namespace, client: object) -> object`.
- CLI surface: `events list|get`, `markets list|get|search|bbo|book|settlement`, `account balances`, `portfolio positions|activity`, `orders list|get`.
- List/filter commands accept optional `--params-json`; `get` commands use exact `--id` or `--slug`; search accepts a positional query plus optional `--params-json` merged with `query`.

- [ ] **Step 1: Write failing tests using a fake SDK client**

Pin method routing and arguments for event lookup, market search/BBO/book, balances, positions, open orders, and unknown read command rejection.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_read_commands.py -q`
Expected: FAIL because read routing is missing.

- [ ] **Step 3: Implement read routing and argparse subcommands**

No read command retries inside this layer. Always close clients exposing `close()` in a `finally` block from the CLI entrypoint.

- [ ] **Step 4: Verify GREEN and full suite**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_read_commands.py -q`
Expected: PASS.

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "feat: add Polymarket US read commands"`

### Task 3: Order preview adapter and one-time confirmation store

**Files:**
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/confirmation.py`
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/trading.py`
- Modify: `.agents/skills/polymarket-us/scripts/pmus.py`
- Create: `.agents/skills/polymarket-us/tests/test_confirmation.py`
- Create: `.agents/skills/polymarket-us/tests/test_preview.py`

**Interfaces:**
- Produces: `canonical_payload(action: str, payload: dict[str, object]) -> bytes`.
- Produces: `ConfirmationStore(root: Path | None = None, ttl_seconds: int = 300)` with `issue(action: str, payload: dict, context: dict | None = None) -> ConfirmationRecord` and `consume(token: str, action: str, payload: dict) -> ConfirmationRecord`.
- Confirmation files store only token hash, action digest, timestamps, and non-secret preview/context; directory mode 0700 and file mode 0600 where supported.
- Produces: `preview_create(client, request: dict) -> dict`, calling current SDK `client.orders.preview({"request": request})`.
- CLI: `orders preview --request-json <object>` returns preview data plus `confirmationToken`, `expiresAt`, and normalized request.

- [ ] **Step 1: Write failing tests for token lifecycle and preview contract**

Tests include issue/consume once, expiry, action mismatch, payload mismatch, raw token not persisted, and SDK preview call receiving `{"request": request}`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_confirmation.py .agents/skills/polymarket-us/tests/test_preview.py -q`
Expected: FAIL because confirmation/trading modules are missing.

- [ ] **Step 3: Implement the confirmation store and preview adapter**

Use `secrets.token_urlsafe`, SHA-256 for token filenames/action digests, atomic create/replace operations, and wall-clock expiry suitable across separate CLI processes.

- [ ] **Step 4: Verify GREEN and full suite**

Run focused tests, then `python -m pytest -q`.
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "feat: add guarded order preview confirmations"`

### Task 4: Guarded live order mutations

**Files:**
- Modify: `.agents/skills/polymarket-us/scripts/pmus_core/trading.py`
- Modify: `.agents/skills/polymarket-us/scripts/pmus.py`
- Create: `.agents/skills/polymarket-us/tests/test_live_orders.py`

**Interfaces:**
- Produces prepare functions for non-create actions: `prepare_modify`, `prepare_cancel`, `prepare_cancel_all`, `prepare_close_position`; each fetches current relevant state and issues a confirmation token bound to the requested mutation.
- Produces execute functions `create_order`, `modify_order`, `cancel_order`, `cancel_all_orders`, `close_position`; each consumes the matching token before invoking the SDK exactly once.
- CLI commands: `orders create`; `orders prepare-modify|modify`; `orders prepare-cancel|cancel`; `orders prepare-cancel-all|cancel-all`; `positions prepare-close|close`.
- Every mutation takes its full action parameters again at execution so token validation can detect any change.

- [ ] **Step 1: Write failing tests for guarded mutations**

Pin: missing token blocks SDK call; mismatched token blocks SDK call; valid token invokes SDK once; consumed token cannot repeat; timeout/connection exception returns structured `ambiguous=true`, `retrySafe=false` and does not perform a second SDK call.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_live_orders.py -q`
Expected: FAIL because mutation functions/commands are missing.

- [ ] **Step 3: Implement prepare and execute paths**

For ambiguous errors, do not retry automatically. Include a recovery hint naming the read command to inspect (`orders get`, `orders list`, or portfolio positions) before any new attempt.

- [ ] **Step 4: Verify GREEN and full suite**

Run focused test, then `python -m pytest -q`.
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "feat: add confirmed live order actions"`

### Task 5: Official-doc freshness checker and skill references

**Files:**
- Create: `.agents/skills/polymarket-us/scripts/check_docs.py`
- Create: `.agents/skills/polymarket-us/scripts/pmus_core/docs_check.py`
- Modify: `.agents/skills/polymarket-us/scripts/pmus.py`
- Create: `.agents/skills/polymarket-us/references/official-sources.md`
- Create: `.agents/skills/polymarket-us/references/api-workflows.md`
- Create: `.agents/skills/polymarket-us/references/trading-safety.md`
- Create: `.agents/skills/polymarket-us/tests/test_docs_check.py`

**Interfaces:**
- Produces: `parse_docs_index(text: str) -> list[DocEntry]`; `check_required_docs(fetcher=...) -> dict`.
- Required index entries include authentication, rate limits, create/preview/modify/cancel/close order, events, markets BBO/book, portfolio, account, search, Python SDK quickstart/orders, and WebSockets overview.
- CLI: `docs-check` returns JSON and exits nonzero when required official pages disappear from the index.

- [ ] **Step 1: Write failing parser/checker tests using a fixture string**

- [ ] **Step 2: Run focused test and verify RED**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_docs_check.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement bounded `llms.txt` fetch and references**

Use stdlib `urllib`; do not crawl the full site. References document the official-source precedence and the known current SDK-doc preview shape discrepancy.

- [ ] **Step 4: Verify tests and one live docs-check**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_docs_check.py -q && python .agents/skills/polymarket-us/scripts/check_docs.py`
Expected: tests PASS and live result reports `ok: true`.

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "feat: add official Polymarket US docs checks"`

### Task 6: Canonical `SKILL.md` and cross-agent installer

**Files:**
- Create: `.agents/skills/polymarket-us/SKILL.md`
- Create: `.agents/skills/polymarket-us/references/agent-installation.md`
- Create: `scripts/install-skill.py`
- Create: `tests/test_install_skill.py`

**Interfaces:**
- `SKILL.md` frontmatter: name `polymarket-us`; description triggers on Polymarket US market research, portfolio/account inspection, API development, previews, and order actions.
- Skill flow: identify US vs International; run docs check when freshness criteria apply; use CLI rather than hand-rolling auth/API paths; read-only actions may run; live actions must prepare/preview, present exact summary, receive explicit user confirmation, then execute with token.
- Produces installer function `install(repo_root: Path, target: str, force: bool = False) -> InstallResult`.
- `codex` and `antigravity`: verify canonical `.agents/skills/polymarket-us` and make no duplicate copy.
- `claude`: create `.claude/skills/polymarket-us` symlink to canonical skill when possible, copy fallback only when requested/required.
- `hermes`: prefer project discovery; report the exact `hermes skills trust <repo-root>` command rather than mutating `~/.hermes/config.yaml` silently.

- [ ] **Step 1: Write failing installer tests**

Pin codex/antigravity no-op, Claude relative symlink target, collision refusal without `--force`, and Hermes trust instruction.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest tests/test_install_skill.py -q`
Expected: FAIL because installer does not exist.

- [ ] **Step 3: Implement installer and skill instructions**

Keep `SKILL.md` concise; move platform details and API examples into references for progressive disclosure.

- [ ] **Step 4: Verify GREEN and full suite**

Run focused test, then `python -m pytest -q`.
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "feat: add portable agent skill installation"`

### Task 7: README, CI, lint, and end-to-end verification

**Files:**
- Create: `README.md`
- Create: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` as needed for final pytest/ruff configuration
- Create: `.agents/skills/polymarket-us/tests/test_cli.py`

**Interfaces:**
- README documents Python setup, `polymarket-us>=1.0.2,<2`, environment credentials, install targets, read examples, preview-confirm-execute example, testing, and non-goals.
- CI runs on Python 3.10 and current stable Python: install `.[dev]`, `ruff check .`, `pytest -q`.
- CLI smoke tests execute `pmus.main([...])` with fake clients/store and assert JSON output/exit codes for one read flow, preview flow, and confirmed mutation flow.

- [ ] **Step 1: Write failing CLI smoke tests before final wiring**

- [ ] **Step 2: Run smoke tests and verify RED**

Run: `python -m pytest .agents/skills/polymarket-us/tests/test_cli.py -q`
Expected: at least one test FAIL on missing final CLI wiring.

- [ ] **Step 3: Complete CLI wiring, README, and CI**

- [ ] **Step 4: Run final verification**

Run: `ruff check .`
Expected: exit 0.

Run: `python -m pytest -q`
Expected: all tests PASS.

Run: `python .agents/skills/polymarket-us/scripts/check_docs.py`
Expected: `ok: true` against current official docs.

Run: `python .agents/skills/polymarket-us/scripts/pmus.py --help`
Expected: exit 0 and documented command groups.

- [ ] **Step 5: Commit**

`git commit -m "docs: finish Polymarket US agent skill"`

## Plan Self-Review

- Spec coverage: canonical skill, market/account reads, official-doc freshness, credentials, preview/confirmation, all v1 single-order mutations, cross-agent installation, testing, README, and non-goals are assigned to tasks.
- Interface consistency: Tasks 2–5 consume Task 1's client/output boundary; Task 4 consumes Task 3's confirmation store; Task 7 consumes all prior CLI interfaces.
- SDK drift: preview request-shape discrepancy is deliberately hidden behind `preview_create()` and contract-tested.
- Scope: no batch/RFQ/combo/WebSocket daemon implementation is introduced.
- Proportion: the plan fixes interfaces and tests but leaves function bodies to implementation.