# SpecPack — Rebuildable Personal Software, Not Clones

> Open-source the **recipe & invariants**, so each person gets *their* meal.

AI agents can build almost any small piece of software. The result is a flood
of one-off apps — "slop": built because they *could* be built, used by nobody a
week later, or published only as finished code tuned to one author's taste.

SpecPack is an experiment in a different unit of open source:

**Publish a compact pack — core invariants, hard-won dead ends, and a
personalisation interview — so another person can hand it to *their* agent and
build a version shaped around *their* workflow, surface, and aesthetic.**

Two agents rebuilding the same pack **should not produce identical twins**. They
should protect the same core truths while differing freely in UI form factor,
visual taste, stack, and extras.

## What belongs in a SpecPack

SpecPack makes the most sense for **regenerable, UI- or workflow-heavy personal
tools** (`< 3 days`, `< 50 conversations`, or `< 50M tokens`):

- **Great fit:** menu-bar utilities, local dev control planes, personal
  dashboards, triage/review companions, or interaction-rich workflows where
  different people legitimately want different surfaces and styles.
- **Not a fit:** pure single-purpose CLIs and libraries (share a normal
  reusable package like `brew install`), or systems built on proprietary data,
  payments, or live multi-user network effects (maintain the shipped product).

## The 3 layers of a pack (v0.2)

```
my-pack/
  pack.yaml       # manifest: name, format_version, budgets, measured runs
  SKILL.md        # freedom-by-default instructions + Personalisation Interview
  spec.md         # LOCKED CORE: ~5–15 testable invariants ([1.1]) + non-goals
  decisions.md    # ADVISORY: reference choices, dead ends/traps, taste calls
  examples/       # concrete scenario/input -> expected outcome fixtures
  reference/      # one creator's screenshots/demos as inspiration (NOT pixel law)
  tests/          # outcome/scenario invariant tests (JUnit XML -> eval/score.py)
  eval.md         # how core invariants & chosen personalisations are verified
```

Only **`spec.md` (Core Invariants + Non-goals)** is a strict contract:
- `decisions.md` shares traps you hit and choices you made *as advice*, not orders.
- `reference/` shows one author's taste as a moodboard, never a pixel gate.
- `SKILL.md` runs a lightweight `/grill-me`-style **Guided Taste Interview** *before coding* — one product/UX question at a time with recommended defaults and zero plumbing jargon — so the rebuild fits how the user wants to work.

See [FORMAT.md](FORMAT.md), the [validator](eval/validate.py), the
[JUnit/JSON scorer](eval/score.py), the
[clean-room trial scaffolder](eval/prepare_run.py), the
[side-by-side comparator](eval/compare.py), the
[pack harvester skill](skills/harvest-specpack/SKILL.md), and the reference packs
([Port Tools](examples/port-tools/) and [Signal](examples/signal/)).

## The experiment

Can different agent harnesses, given **only a pack** (no original source code),
build **distinct, personally tailored apps** that still preserve **every core
invariant** cleanly and cheaply?

Protocol and results log: [experiment/](experiment/)

1. Pick a real workflow/UI-rich tool (for example a local port & dev control plane).
2. Harvest a compact pack from building it — stripping implementation lock-in down to invariants, dead ends, and taste calls.
3. Hand the pack, cold, to different harnesses (`Codex`, `Claude Code`, `Cursor`, `Antigravity`, `OpenCode`) with different user personalisation choices.
4. Record: harness, model, chosen surface/style, wall time, rounds, tokens, and `Invariants %` from real test execution.
5. Publish both wins and gaps — any missing invariant or surprising drift improves the format.

## Principles

1. **Invariants over blueprints.** Lock *what must stay true*; leave *how it looks and runs* free.
2. **Warn on traps, don't dictate choices.** Share dead ends (`decisions.md`) so rebuilders don't suffer twice without forcing your stack.
3. **Personalise before coding.** A rebuild without an intentional surface/taste choice is just a slower copy.
4. **Tests prove invariants.** Scenario & outcome tests matter; screenshots are only inspiration.
5. **Report the cost.** Every rebuild records surface, time, rounds, tokens, and gaps honestly.

## Status

**v0.2** — reworked around freedom by default (`spec.md` core invariants, advisory `decisions.md`, `SKILL.md` one-question-at-a-time Guided Taste Interview, `reference/` moodboard), backed by `eval/validate.py` and `eval/score.py`. Includes **[Port Tools](examples/port-tools/)** (first full harvested UI-heavy reference pack) alongside **[Signal](examples/signal/)**.

## License

MIT
