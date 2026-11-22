---
name: my-pack
description: Build your own version of <thing> protecting core invariants while tailoring surface, style, and workflows to you.
---

# How to build this (Freedom by Default)

1. **Read `spec.md` strictly.** Its non-goals and ~5–15 bracketed invariants (`[1.1]`, ...) are the only locked contract.
2. **Read `decisions.md` as field notes, not orders.** Reuse what fits; replace reference choices freely if your version works better a different way, while avoiding listed dead ends.
3. **Run a lightweight `/grill-me`-style Guided Taste Interview before writing code.** Walk through the **Personalisation Interview** **one high-level product/UX question at a time** — give 2–4 plain-language options with one `(Recommended)` choice, honor `"just use defaults"` at any point, skip questions made irrelevant by earlier answers, and never ask about low-level plumbing (languages, sockets, schemas, timeouts) unless the human asks:
   - **Surface & form factor:** <e.g. menu bar app (Recommended) / local web dashboard / TUI / command launcher>
   - **Primary mental model:** <e.g. project-first workspace view (Recommended) / triage queue / search-first launcher>
   - **Visual vibe & density *(skip if TUI / headless)*:** <e.g. quiet native / crisp Linear minimal (Recommended) / dense developer table>
   - **Optional personal extras:** <any extra shortcuts or workflow tweaks tailored to the user, or keep minimal (Recommended)>
4. **Glance at `reference/` only as inspiration.** One author's screenshots are a moodboard, never a layout target.
5. **Run `eval.md` checks** and report: chosen surface/style, `Invariants %`, tokens, wall time, rounds, and any failed/unverified invariant IDs.
