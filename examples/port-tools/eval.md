# Evaluating a Port Tools Rebuild (`eval.md`)

Run these checks from `examples/port-tools` (paths adjust naturally if invoked from repo root).

## 1. Validate pack structure

```bash
python3 ../../eval/validate.py . --strict
```

Must pass with `0` errors and `0` warnings.

## 2. Verify harness fixtures cleanly (`--self-test`)

```bash
python3 tests/contract_harness.py --self-test
```

Spins up disposable local IPv4/IPv6 HTTP, Swagger/DevTools, raw TCP, WebSocket upgrade, SSE, dual Git worktree, and process-lifecycle fixtures to verify the test harness itself on this host.

## 3. Run the contract suite against a rebuilt implementation

A rebuilding agent wires any language/UI implementation via a small CLI adapter (`--adapter`) implementing four subcommands over temporary isolated state:

```text
<adapter> scan --state-dir <dir>
<adapter> alias set --alias <name> --pid <pid> --port <port> --state-dir <dir>
<adapter> stop-plan --pid <pid> --state-dir <dir>
<adapter> stop --plan-token <token> [--force] --state-dir <dir>
<adapter> init-routes --state-dir <dir>   # used for corrupt route recovery test [3.3]
```

Run the contract harness to produce JUnit XML and score directly against `spec.md`:

```bash
python3 tests/contract_harness.py \
  --adapter "path/to/your-adapter" \
  --junit-out junit-port-tools.xml

python3 ../../eval/score.py \
  --junit junit-port-tools.xml \
  --spec spec.md \
  --surface "<your chosen surface & taste>" \
  --json-out run-report.json
```

Target: **`INVARIANTS: 12/12 = 100.0%`** with zero skipped or unverified `[1.1]`–`[4.3]` IDs.

## 4. Human smoke checklist (matches Guided Taste Interview choices)

- Launch the rebuilt surface chosen in `SKILL.md` (menu bar / web UI / TUI / launcher).
- Confirm openable dev Web UIs appear cleanly separated from secondary `Other Web endpoints` and `Other listeners`.
- Open a mapped `{alias}.localhost` URL in a browser and confirm hot-reload / WebSocket updates work with zero OS keychain/admin/hosts prompts.
- Preview stop on a Docker-published port (must refuse safely) and stop one disposable test server cleanly.

## Required run report fields

| Field | Value |
| --- | --- |
| Surface & taste profile | chosen surface, mental model, visual vibe, extras |
| `Invariants %` | e.g. `100.0%` (`12/12`) |
| Tokens / Wall time / Rounds | actual measured budget figures |
| Failed or unverified IDs | list or `none` |
