# SpecPack Format v0.2

A pack is a self-contained directory that gives a stranger's agent enough clarity
to build **their own version** of a small, UI- or workflow-rich tool without
accessing the original codebase.

Think in **3 strictness layers** — keep Layer 1 small, Layer 2 honest, and Layer 3 wide open:

## 1. Locked Core (`spec.md`)
Keep `spec.md` intentionally lean (~**5–15 non-negotiable invariants**, not an
exhaustively micro-managed clone spec):
- **`## Non-goals`:** what the software deliberately refuses to do (safety bounds, bloat guardrails).
- **Bracketed Invariants:** testable EARS or Given/When/Then outcomes tagged with unique hierarchical IDs:
  `- [1.1] WHEN <event> THEN the system SHALL <invariant>`
  `- [1.2] IF <condition> THEN the system SHALL <invariant>`
- **No implementation lock-in:** do NOT mandate language, UI framework, color palette, window type, IPC transport, or menu layout inside `spec.md` unless a domain invariant genuinely depends on it.

## 2. Advisory Field Notes (`decisions.md` + `pack.yaml`)

### `decisions.md`
Shared **as advice, not orders**. Rebuilders may replace any architecture choice unless doing so would violate `spec.md`:
- `## Reference choices (advisory)` — stack/architecture used in the reference build, rationale, and clean alternatives.
- `## Dead ends & traps` — OS quirks, subtle race conditions, broken APIs, and failed approaches discovered while building.
- `## Taste calls` — intentional design stances (e.g. density, safety friction, local-only stance) offered as inspiration.

### `pack.yaml`
```yaml
name: my-pack
format_version: "0.2"
version: 0.1.0
description: One sentence: what problem this solves and who it is for.
regenerability:
  budget_days: 3
  budget_conversations: 50
  budget_tokens: 50000000   # 50M tokens default small-software ceiling; packs set their own
  measured:                 # filled in by rebuild runs, not by the author
    - harness: ""
      model: ""
      surface: ""           # e.g. "macOS menu bar (SwiftUI)", "Web UI (React)", "TUI", "Raycast"
      wall_time: ""
      conversations: 0
      tokens: 0
      invariants_percent: 0
license: MIT
```

## 3. Personalisation Canvas (`SKILL.md` + `reference/`)

### `SKILL.md`
Entry point for the rebuilding agent.
- YAML frontmatter `name:` MUST match `pack.yaml` `name:`.
- Must teach **freedom by default**: obey `spec.md` invariants & non-goals strictly; treat `decisions.md` and `reference/` strictly as advice and inspiration.
- MUST include a **Personalisation Interview** structured as an adaptive, `/grill-me`-style **Guided Taste Interview** *before writing code*:
  - **Never hardcode a fixed numbered questionnaire** (no rigid `Q1–Q5` script or canned A/B/C/D survey form). Give the agent **open taste dimensions** (a compass of freedom axes) and let it run a natural conversation tailored to the user's answers.
  - Ask **one short high-level product/UX question at a time**, adapt each next question based on what the human actually answered, and stop early once the product shape is clear (`3–5` turns typical).
  - Give concrete directions or trade-offs with one `(Recommended)` choice per turn, and honor `"just use defaults"` at any moment.
  - **Keep plumbing out of the interview:** do not ask about sockets, languages, timeouts, schemas, or internal protocols unless the human brings them up — make clean engineering choices internally.

### `reference/` (replaces `golden/` from v0.1)
Screenshots, GIFs, or sample exports of **one creator's version**, labeled as inspiration/moodboard rather than a target to replicate. Never fail a rebuild because it chose a different layout or aesthetic.

## Verification Artifacts (`examples/`, `tests/`, `eval.md`)

### `examples/`
Concrete input/state scenarios and domain edge-case fixtures named after criterion IDs (e.g., `1.2-fixture.json`), usable across stacks/surfaces.

### `tests/`
Executable **outcome / invariant tests** verifying `spec.md` without locking UI layout or internal stack (fixture-driven checks, CLI/HTTP/core harness tests, Playwright role/outcome checks), emitting **JUnit XML** referencing `[1.1]` or `1_1` IDs in test names.

### `eval.md`
Documents:
- how to run the invariant suite (`--junit results.xml --spec spec.md`)
- `Invariants % = passed invariants / total invariants in spec.md` (untested/skipped criteria count as failed/unverified)
- how the rebuild's **chosen personalisations** were exercised and confirmed with the user
- required run report fields (see `experiment/PROTOCOL.md`)

## Tooling
- `python3 eval/validate.py <pack_dir> [--strict]` — checks required/recommended paths (recognizing `reference/` and warning cleanly on legacy `golden/`), `pack.yaml` schema, `SKILL.md` frontmatter `name` parity + personalisation prompt presence, unique `[X.Y]` IDs, `## Non-goals` / `## Dead ends` / `## Taste calls`, and unfilled `<placeholders>`.
- `python3 eval/score.py --junit <results.xml> --spec <spec.md> [--surface "..."]` — computes per-area and total **`Invariants %`** strictly from executed tests.

## Rules
1. Lock outcomes and safety; free form factor and taste.
2. One invariant ID = one checkable domain truth.
3. Ask personalisation preferences first; record choices honestly.
4. Reference screenshots are approved by a human and shared as inspiration only.
