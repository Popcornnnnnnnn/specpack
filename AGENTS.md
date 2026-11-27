# SpecPack working agreement

For major updates or changes to `eval/` validation, scaffolding, scoring, or comparison, run the Python tests and follow the [eval lifecycle verification skill](.agents/skills/verify-eval-lifecycle/SKILL.md) before delivery. Check for drift from `sync_commit`, run TLC through `/statechart`, and replay any counterexample against the Python entry point.
