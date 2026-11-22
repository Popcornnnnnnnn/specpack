---
name: harvest-specpack
description: Harvest a freedom-by-default SpecPack (v0.2) from an existing UI- or workflow-rich build without locking rebuilders into clones.
---

# Harvest a SpecPack From a Real Build (v0.2)

Use this workflow after (or during) building a regenerable, UI- or workflow-rich tool (`< 3 days`, `< 50 conversations`, or `< 50M tokens`) to distill a portable pack in `packs/<name>/` or `examples/<name>/`.

## 1. Check Fit & Regenerability First
- Target software with **UI, personal workflows, or opinionated interaction logic** where different users legitimately want different form factors, styles, and extras.
- Skip pure single-purpose CLIs and libraries — share those as normal reusable packages (`brew install`, `pip`, etc.).
- Skip apps whose core depends on proprietary data, payments, or live multi-user network effects that a local rebuild cannot simulate cleanly.

## 2. Create Pack Skeleton
Copy `templates/pack/` into the target directory, set `pack.yaml` (`name`, `format_version: "0.2"`, `version`, one-sentence `description`, realistic budgets, `measured: []`), and match `SKILL.md` frontmatter `name:` to `pack.yaml`.

## 3. Distill Only the Locked Core (`spec.md`)
Keep `spec.md` compact (~**5–15 core invariants** plus `## Non-goals`):
- Write only what must remain true across *every* rebuild (safety guardrails, domain attribution rules, state invariants).
- Strip framework, language, visual theme, IPC, and window-layout mandates out of `spec.md` so agents are free to pick a different stack or surface.
- Format each invariant as `- [1.1] WHEN ... THEN the system SHALL ...` or Given/When/Then.

## 4. Harvest Field Notes as Advice (`decisions.md`)
From git history, issues, PRs, and session memories, separate:
- **`## Reference choices (advisory)`**: what the reference build picked and why — explicitly optional to swap.
- **`## Dead ends & traps`**: OS quirks, subtle race bugs, and failed paths rebuilders must avoid repeating.
- **`## Taste calls`**: one creator's intentional UX/density stances shared as inspiration.

## 5. Write the Personalisation Interview (`SKILL.md` + `reference/`)
- Author **3–5 concrete questions** in `SKILL.md` that a rebuilding agent asks *before coding*:
  - Which surface fits the user (menu bar, Web dashboard, Raycast, TUI, mobile companion)?
  - Which visual vibe and density feel right?
  - Which extras to add or drop?
  - Which language/stack they prefer on their machine?
- Put human-approved screenshots/demos of your build into `reference/` with brief captions explaining taste choices — explicitly labeled as inspiration, never a pixel gate.

## 6. Build Surface-Independent Verification (`examples/` & `tests/`)
- Add realistic domain fixtures to `examples/` (`1.2-fixture.json`).
- Write outcome/scenario tests in `tests/` that prove `spec.md` invariants without locking UI structure or language internals, emitting **JUnit XML** referencing `[1.1]` or `1_1` IDs.

## 7. Validate & Gate
```bash
python3 eval/validate.py <pack_dir> --strict
```
Fix all errors and warnings before publishing or running cross-harness rebuilds.
