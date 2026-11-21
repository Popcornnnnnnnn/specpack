# Rebuild Experiment Protocol

## Question
Given **only a pack** (no original source code, no author help), how well,
how fast, and at what token cost can different agent harnesses rebuild the
software?

## Rules
1. The rebuilding agent gets the pack directory and nothing else from the
   original project. No original repo, no screenshots beyond `golden/`.
2. The human operator may answer only questions the pack's SKILL.md marks
   as personalisation points. All other questions are logged as pack gaps.
3. One run = one harness + one model, starting from an empty directory.
4. Stop conditions: eval passes, budget in pack.yaml is exhausted, or the
   operator stops the run. Record which one happened.
5. No fixing the pack mid-run. Gaps found are data — log them, finish, then
   revise the pack and re-run as a new run.

## Record for every run (append to RESULTS.md)
Harness, model, date, operator, wall time, conversations and rounds,
tokens in/out/total, parity % (total and per requirement area), failed
criterion IDs, pack gaps found, personalisation choices.

## Interpretation
- **>= 90% parity:** pack is sufficient; differences are personalisation.
- **70–89%:** pack is close; failed criteria show what to specify better.
- **< 70%:** the idea, the pack, or the format is missing something real.
  Publish it anyway — that is the finding.
