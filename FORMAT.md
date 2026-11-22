# SpecPack Format v0.1

A pack is a directory. All text files are Markdown unless noted.
An agent must be able to build the software using **only** the pack.

## Required files

### pack.yaml
```yaml
name: my-pack
version: 0.1.0
description: One sentence: what this is and who it is for.
regenerability:
  budget_days: 3
  budget_conversations: 50
  budget_tokens: 50000000   # 50M tokens default small-software ceiling; packs set their own
  measured:                 # filled in by rebuild runs, not by the author
    - harness: ""
      model: ""
      wall_time: ""
      conversations: 0
      tokens: 0
      parity_percent: 0
license: MIT
```

### SKILL.md
Entry point for the loading agent. YAML frontmatter `name` MUST match `pack.yaml` `name`. States: purpose, how to read the pack (`spec.md` first, then `decisions.md`), build order, how to run `eval`, and what to ask the human vs. decide itself (personalisation points).

### spec.md
Numbered, testable acceptance criteria using bracketed hierarchical IDs:
`- [1.1] WHEN <event> THEN the system SHALL <response>`
or Given/When/Then tagged with `- [1.2] ...`.
Every criterion ID (e.g. `1.1`, `1.2`, `2.1`) MUST be unique and referenced by tests in `tests/`.
Must include: user stories, criteria, explicit `## Non-goals`, and measurable success conditions. No implementation detail here.

### decisions.md
Architecture/design decisions in ADR style (choice, rationale, alternatives considered), plus `## Dead ends` discovered while building and `## Taste calls` a rebuilder should know are intentional, not accidental.

## Recommended files

### examples/
Input -> expected-output fixtures (JSON/text), named after the criterion ID they illustrate, e.g. `1.2-input.json`, `1.2-expected.json`.

### golden/
Visual and output references:
- **Deterministic data goldens** (normalized JSON/CLI/text outputs) may be asserted strictly after masking timestamps, UUIDs, and dates.
- **Visual screenshots** (e.g. `home-desktop.png`): use for strict pixel diffs **only** on locked non-personalized views; whenever layout or theme is listed as a personalisation point in `SKILL.md`, treat screenshots as **style references** and verify behaviour through contract tests instead.

### tests/
Executable **contract tests** that check `spec.md` criteria without locking personalisable look-and-feel (CLI flags, HTTP/JSON schemas, DB invariants, DOM roles/assertions, JUnit XML reporting with criterion IDs such as `[1.1]` or `1_1` in test names).

### eval.md
How parity is scored for a rebuild:
- exact test command and how JUnit XML is produced
- evidence-backed scoring via `python3 eval/score.py --junit <results.xml> --spec spec.md` (or `run-report.json`), reporting per-requirement-area and total parity
- what counts as allowed personalisation vs. contract drift
- required run report fields (see `experiment/PROTOCOL.md`)

## Tooling
- `python3 eval/validate.py <pack_dir> [--strict]` — checks manifest fields, frontmatter/name parity, duplicate/missing criterion IDs, required headings, and unfilled template placeholders.
- `python3 eval/score.py --junit <results.xml> --spec <spec.md>` — scores parity strictly from executed tests mapped to spec criterion IDs (missing/untested or skipped criteria count as failed).

## Rules
1. One criterion = one checkable behaviour.
2. Contract tests prove `spec.md`; UI personalisation is free unless explicitly locked.
3. If it isn't in the pack, the rebuilder may choose freely — and should record the choice as a personalisation, not silently diverge.
4. Goldens are approved by a human. An agent never approves its own golden.
