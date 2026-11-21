# SpecPack Format v0.1 (draft)

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
  budget_conversations: 100
  budget_tokens: 1000000000
  measured:            # filled in by rebuild runs, not by the author
    - harness: ""
      model: ""
      wall_time: ""
      conversations: 0
      tokens: 0
      parity_percent: 0
license: MIT
```

### SKILL.md
Entry point for the loading agent. States: purpose, how to read the pack
(read spec.md first, then decisions.md), build order, how to run eval,
and what to ask the human vs. decide itself (personalisation points).

### spec.md
Numbered, testable acceptance criteria. Use EARS
(`WHEN <event> THEN the system SHALL <response>`) or Given/When/Then.
Every criterion has an ID (e.g. `1.2`) that tests and tasks reference.
Must include: user stories, criteria, explicit **non-goals**, and
measurable success conditions. No implementation detail here.

### decisions.md
Architecture/design decisions in ADR style (choice, rationale,
alternatives considered), plus dead ends discovered while building and
taste calls a rebuilder should know are intentional, not accidental.

## Recommended files

### examples/
Input -> expected-output fixtures (JSON/text), named after the criterion
ID they illustrate, e.g. `1.2-input.json`, `1.2-expected.json`.

### golden/
Approved screenshots (per viewport/browser, e.g.
`home-desktop-chromium-linux.png`) and/or golden output files.
Volatile values (timestamps, UUIDs) must be masked/frozen — see eval.md.

### tests/
Executable acceptance tests that check spec.md criteria:
Gherkin `.feature` files, Playwright tests (incl. `toHaveScreenshot()`
against `golden/`), or the stack's native test runner.

### eval.md
How parity is scored for a rebuild:
- which tests/goldens are run, and the exact command
- parity = passed criteria / total criteria (report per-area, not just total)
- what counts as a personalisation difference (allowed) vs. drift (failure)
- required run report format (see experiment/PROTOCOL.md)

## Rules
1. One criterion = one checkable behaviour.
2. If it isn't in the pack, the rebuilder may choose freely — and should
   record the choice as a personalisation, not silently diverge.
3. Goldens are approved by a human. An agent never approves its own golden.
