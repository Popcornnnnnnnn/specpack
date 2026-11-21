# SpecPack — Rebuildable Software, Not Slop

> Open-source the **recipe**, not just the meal.

AI agents can now build almost any small piece of software. The result is a
flood of one-off apps — "slop": built because they *could* be built, used by
nobody a week later, and impossible for anyone else to reproduce, learn from,
or adapt.

SpecPack is an experiment in a different unit of open source:

**Instead of (only) publishing the finished product, publish a pack —
a PRD / handbook / skill — that lets another person load it into *their*
agent and rebuild their own version, tailored to themselves.**

UI, features, and details should differ per person. The intent, decisions,
and verifiable definition of "done" are what's shared.

## The regenerability test

A piece of software is a good candidate for a SpecPack if it is
**regenerable**:

- buildable in **< 3 days** of agent-assisted work, **or**
- **< 100 conversations** (≈100 rounds of communication each) with an agent, **or**
- **< 1B tokens** total build cost.

Below that threshold, implementation is a commodity and the specification
*is* the product. Above it (data, network effects, trust, payments, ongoing
operations), people usually need the maintained product itself — publish the
code too.

## What is a pack?

```
my-pack/
  pack.yaml       # manifest: name, version, regenerability budget, scores
  SKILL.md        # how an agent should load and build this
  spec.md         # numbered acceptance criteria (EARS or Given/When/Then)
  decisions.md    # key decisions, alternatives rejected, dead ends, taste calls
  examples/       # input -> expected output fixtures
  golden/         # approved screenshots / golden outputs
  tests/          # executable acceptance tests (.feature, Playwright, ...)
  eval.md         # how parity is scored
```

No single existing standard bundles all of this:

- **Spec format:** GitHub Spec Kit (`constitution/spec/plan/tasks`) and
  Amazon Kiro (`requirements/design/tasks`, EARS criteria) cover spec->plan.
- **Golden / approval testing:** golden files, Jest/insta snapshots, and
  Playwright `toHaveScreenshot()` cover "approved output" for code that
  already exists.
- **SpecPack adds the missing piece:** an `eval` that a *rebuilding* agent
  runs cold, reporting parity %, tokens, time, and rounds — so a pack is
  reproducible and *scored*, not just documented.

See [FORMAT.md](FORMAT.md) for the v0.1 format.

## The experiment

Can a stranger's agent, given **only a pack** (no original code), rebuild a
working version at high parity — cheaply?

Protocol and results log: [experiment/](experiment/)

1. Pick a small real app (first candidate: a personal "Signal" daily
   tech/open-source digest).
2. Build it once, capturing the pack *as a byproduct* of building —
   specs, screenshots, tests, decisions — not as after-the-fact paperwork.
3. Hand the pack, cold, to different agent harnesses (e.g. Muse,
   Codex, Cursor, Antigravity, OpenCode).
4. Each run records: harness, model, wall time, conversations/rounds,
   tokens, and a parity score against the pack's tests and goldens.
5. Publish the results, including failures. A pack that rebuilds at 50%
   teaches us exactly what the format is missing.

## Principles

1. **Capture, don't document.** The pack should be harvested from the build
   session, then reviewed/approved by a human — never authored from scratch
   afterwards.
2. **Tests over prose.** A criterion that can't be checked doesn't count.
3. **Non-goals are first-class.** What the software must *not* do prevents
   most rebuild drift.
4. **Personal is not slop.** Slop is low-intent: built, unused, unreproducible.
   A tiny tool used daily by its one builder is a success — and its pack
   lets the next person make *their* version.
5. **Report the cost.** Every rebuild states tokens/time/rounds honestly.

## Status

v0.1 — format draft, templates, and experiment protocol. No reference pack
has completed a cross-harness rebuild yet; that is the first milestone.

## License

MIT
