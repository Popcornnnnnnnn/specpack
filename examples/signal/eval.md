# Eval — how parity is scored

## Command
Run the contract test suite and emit JUnit XML, then score against `spec.md`:
`<exact command that runs tests/ and writes results.xml>`

```bash
python3 eval/score.py --junit results.xml --spec spec.md --json-out run-report.json
```

## Scoring
- Parity % = passed acceptance criteria / total criteria in `spec.md` (criteria with zero executed tests count as failed/unverified).
- Report per requirement area, plus a total.
- **Deterministic outputs** (JSON/CLI/text goldens): mask timestamps, UUIDs, and dates before comparing.
- **Visual screenshots** in `golden/`: treat as style references whenever UI/theme is marked as a personalisation point in `SKILL.md`; use strict pixel diffs only on explicitly locked screens.

## Allowed personalisation (not drift)
- <listed in SKILL.md>

## Run report (required)
| Field | Value |
|---|---|
| Harness | |
| Model | |
| Wall time | |
| Conversations / rounds | |
| Tokens (in/out, total) | |
| Parity % | |
| Failed criteria (IDs) | |
| Personalisation choices made | |
