---
name: harvest-specpack
description: Harvest a rebuildable SpecPack from an existing codebase or build session instead of writing post-hoc prose.
---

# Harvest a SpecPack From a Real Build

Use this workflow after (or during) building a small, regenerable piece of software (`< 3 days`, `< 50 conversations`, or `< 50M tokens`) to capture a self-contained pack in `packs/<name>/` or `examples/<name>/`.

## 1. Check Regenerability First
- Confirm the core value does **not** depend on proprietary datasets, live multi-user network effects, payments, or external accounts that a stranger's agent cannot reproduce cleanly with local fixtures or mocks.

## 2. Create Pack Skeleton
Copy `templates/pack/` into the target pack directory, set `pack.yaml` (`name`, `version`, `description`, realistic budgets, `measured: []`), and align `SKILL.md` frontmatter `name:` identically to `pack.yaml`.

## 3. Capture the Contract (`spec.md`)
- Extract **non-goals** first from what was deliberately left out of scope.
- Group behaviours into `### Requirement N: <title>` sections.
- Express each requirement as bracketed EARS or Given/When/Then criteria (`- [1.1] WHEN ... THEN the system SHALL ...`).
- Keep `spec.md` free of framework/library lock-in unless an external binary or protocol is part of the observable contract.

## 4. Harvest Session Memory (`decisions.md`)
From git history, issues, PRs, and session discussions, record:
- **Decisions:** choice, rationale, and rejected alternatives.
- **Dead ends:** approaches tried that failed and must not be repeated during rebuilds.
- **Taste calls:** deliberate UX, density, safety, or simplicity stances.

## 5. Mark Personalisation Points (`SKILL.md` & `eval.md`)
- List what the rebuilding agent should **ask the user or tailor freely** (e.g., visual theme, stack, notification channel, keyboard shortcuts) versus what is strictly locked by `spec.md`.

## 6. Build Evidence (`examples/`, `golden/`, `tests/`)
- Add input -> expected fixtures in `examples/` named after criterion IDs (`1.2-input.json`, `1.2-expected.json`).
- Keep `tests/` as **contract tests** that verify `spec.md` behaviour without pixel-locking personalisable UI, emitting **JUnit XML** where each test name/classname includes its criterion ID (e.g., `test_1_1_...` or `[1.1]`).
- Add only **human-approved** outputs/style references in `golden/`.

## 7. Validate & Gate
```bash
python3 eval/validate.py <pack_dir> --strict
```
Fix all errors and warnings before publishing or running cold-rebuild benchmarks.
