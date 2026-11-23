---
name: my-pack
description: Build your own version of <thing> protecting core invariants while tailoring surface, style, and workflows to you.
---

# How to build this (Freedom by Default)

1. **Read `spec.md` strictly.** Its non-goals and ~5–15 bracketed invariants (`[1.1]`, ...) are the only locked contract.
2. **Read `decisions.md` as field notes, not orders.** Reuse what fits; replace reference choices freely if your version works better a different way, while avoiding listed dead ends.
3. **Run an adaptive, `/grill-me`-style Guided Taste Interview before writing code.**
   Do **not** recite a fixed script or dump multiple questions at once. Use the **Personalisation Interview** compass below to guide a brief `3–5` turn conversation — **one high-level product/UX question at a time**, adapting each follow-up to the user's last answer, suggesting concrete options with one `(Recommended)` choice, honoring `"just use defaults"` immediately, stopping early once the shape is clear, and never asking about low-level plumbing (languages, sockets, schemas, timeouts):
   - **Open taste dimensions (compass, not a script):**
     - *Surface & workflow placement:* <how/where the user wants this tool to live>
     - *Information hierarchy & mental model:* <how primary vs secondary items should be organized>
     - *Interaction, feel & density (adapted to chosen surface):* <visual style/density for GUI or Web, keybindings/layout for TUI, or triggers for launcher>
     - *Personal workflow habits & extras:* <what shortcuts or helpers to include or keep minimal>
4. **Glance at `reference/` only as inspiration.** One author's screenshots are a moodboard, never a layout target.
5. **Run `eval.md` checks** and report: chosen surface/style, `Invariants %`, tokens, wall time, rounds, and any failed/unverified invariant IDs.
