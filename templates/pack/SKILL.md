---
name: my-pack
description: Build your own version of <thing> protecting core invariants while tailoring surface, style, and workflows to you.
---

# How to build this (Freedom by Default)

1. **Read `spec.md` strictly.** Its non-goals and ~5–15 bracketed invariants (`[1.1]`, ...) are the only locked contract.
2. **Read `decisions.md` as field notes, not orders.** Reuse what fits; replace reference choices freely if your version works better a different way, while avoiding listed dead ends.
3. **Run the Personalisation Interview before writing code.** Ask the human (or record defaults if they delegate) before designing the build:
   - **Surface & form factor:** <e.g. menu bar app / local web dashboard / TUI / Raycast extension>
   - **Visual taste & density:** <e.g. Linear minimal / Glass / compact developer table / cards>
   - **Workflows to add or drop:** <any extra actions or shortcuts tailored to the user>
   - **Preferred tech stack:** <any stack that builds cleanly on their machine>
4. **Glance at `reference/` only as inspiration.** One author's screenshots are a moodboard, never a layout target.
5. **Run `eval.md` checks** and report: chosen surface/style, `Invariants %`, tokens, wall time, rounds, and any failed/unverified invariant IDs.
