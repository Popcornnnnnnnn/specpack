# Eval — verifying invariants & personalisation

## Command
Run the invariant test suite against your chosen implementation and emit JUnit XML, then score against `spec.md`:
`<exact command that runs tests/ and writes results.xml>`

```bash
python3 eval/score.py --junit results.xml --spec spec.md --surface "<chosen-surface>" --json-out run-report.json
```

## Scoring & Verification
- **`Invariants %`:** passed core invariants / total invariants in `spec.md` (criteria with zero executed or skipped tests count as failed/unverified).
- Report per requirement area, plus total.
- **`examples/` & `reference/`:** verify deterministic domain fixtures strictly after masking timestamps/UUIDs; treat visual files in `reference/` strictly as **inspiration** so customised UI never counts as drift.
- **Personalisation check:** confirm each answer from the `SKILL.md` Personalisation Interview works end-to-end in the rebuilt app.

## Run report (required)
| Field | Value |
|---|---|
| Harness | |
| Model | |
| Chosen surface / style | |
| Wall time | |
| Conversations / rounds | |
| Tokens (in/out, total) | |
| Invariants % | |
| Failed / unverified IDs | |
| Personalisation choices made | |
