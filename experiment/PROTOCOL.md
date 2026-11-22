# Rebuild Experiment Protocol

## Questions
Given **only a pack** (no original source code, no author help):
1. Do rebuilt apps consistently satisfy the pack's **core invariants** (`Invariants %`) reliably and cheaply across agent harnesses?
2. Given different user preferences (surface, aesthetic, workflow tweaks), does the format enable **genuinely distinct, personalised apps** instead of lookalike clones?

## Rules
1. The rebuilding agent gets the pack directory and nothing else from the
   original project (no source code, no private docs). Screenshots in `reference/` are inspiration only.
2. Before coding, the human operator (or simulated persona for benchmark runs)
   answers the pack's **Personalisation Interview** in `SKILL.md` (picking surface, style, and any requested additions/removals). All clarifying questions about *ambiguous core behaviour* are logged as pack gaps.
3. One run = one harness + one model + one stated personalisation brief, starting from an empty directory.
4. Stop conditions: invariant checks + user brief pass, budget in `pack.yaml` is exhausted, or the operator stops the run. Record which happened.
5. No fixing the pack mid-run. Gaps found are data — log them, finish, then revise the pack and re-run as a new run.

## Record for every run (append to RESULTS.md)
Prefer feeding JUnit XML test results into `eval/score.py` (`python3 eval/score.py --junit results.xml --spec <pack>/spec.md --surface "<chosen-surface>" --json-out run-report.json`) so every invariant ID is backed by an executed test rather than self-reported JSON alone.
Record: Harness, model, date, operator, chosen surface/style, wall time,
conversations and rounds, tokens in/out/total, `Invariants %` (total and per requirement area), failed/unverified criterion IDs, pack gaps found, and personalisation choices made.

## Interpretation
- **>= 90% invariants + distinct surface/taste:** the pack protects what matters without blocking creativity.
- **70–89% invariants:** pack core is mostly clear; failed/unverified IDs show missing domain rules or fixtures.
- **< 70% invariants (or near-identical clones despite different prompts):** either invariants were under-specified or `decisions.md`/`reference/` over-constrained the agent. Publish it — that is the finding.
