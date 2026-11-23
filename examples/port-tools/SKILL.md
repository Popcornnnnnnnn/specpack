---
name: port-tools
description: Build your own Port Tools — live local-port discovery, Git/worktree attribution, locked *.localhost reverse proxy, and safe two-step stop review — tailored via an adaptive Guided Taste Interview.
---

# How to build Port Tools (Freedom by Default)

1. **Obey `spec.md` strictly.** Its `## Non-goals` and 12 bracketed Core Invariants (`[1.1]`–`[4.3]`) are the only locked contract. In particular, `{alias}.localhost` reverse proxying is part of the core product contract, not an optional extra.
2. **Read `decisions.md` as field notes, not orders.** Reuse what helps your chosen stack and OS; avoid the documented dead ends and traps. Nothing locks you into macOS, SwiftUI, Go, or a menu bar popover unless the user wants that.
3. **Run an adaptive, `/grill-me`-style Personalisation Interview (`Guided Taste Interview`) before designing or writing code.**
   Treat the taste dimensions below as a **compass, not a fixed questionnaire** — never recite a rigid `Q1–Q5` script or dump a multi-question form:
   - **Ask one short high-level question at a time** in plain language and wait for the user's reply before deciding what to explore next.
   - **Adapt dynamically to their answers:** if they pick a terminal TUI, follow up naturally on keyboard ergonomics, detail layout, or terminal aesthetic instead of GUI chrome; if they pick an attention inbox or command launcher, explore triage/hotkey habits instead.
   - **Offer 2–4 concise directions per turn** with one marked `(Recommended)`, honor `"just use defaults"` at any turn, and **stop early** as soon as the product shape is clear (`3–5` turns typical).
   - **Zero plumbing questions:** never ask about IPC sockets, programming languages, polling intervals, schemas, or OS syscall flags unless the human explicitly raises them — make clean engineering decisions under the hood.

   **Open taste dimensions to explore:**
   - **Where it lives in their workflow (Surface):** e.g. menu bar / system tray popover *(Recommended on desktop)*, local Web dashboard *(great across OSes / split-screen)*, keyboard-first terminal TUI, or command launcher integration.
   - **How listeners are organized (Mental model):** e.g. project/worktree-first *(Recommended — groups repos & branches, keeps raw listeners collapsed)*, attention-first triage queue (`possibly forgotten` and conflicts upfront), or search-first flat list.
   - **Feel, density & interaction (tailored to the chosen surface):**
     - *If GUI / Web:* visual restraint & density (e.g. crisp Linear minimal *(Recommended)*, quiet host-native chrome, or compact developer table).
     - *If Terminal TUI / Launcher:* navigation & detail cadence (e.g. split table + bottom/side inspector, instant search filter, keybinding style).
   - **`{alias}.localhost` URL behavior:** zero-setup unprivileged `http://{alias}.localhost:{port}` everywhere *(Recommended — zero OS prompts)* vs. optional port-free `http://{alias}.localhost` forwarding where supported with automatic `:{port}` fallback.
   - **Personal workflow habits:** e.g. keep focused on core scan/open/copy/alias/safe-stop *(Recommended)*, or include extras they care about (global search hotkey, open Git remote/folder, noisy-helper auto-collapse, or click-to-copy).

4. **Glance at `reference/` strictly as a moodboard.** The screenshots show one macOS author's light/dark menu bar aesthetic — never treat them as a pixel target or platform restriction.
5. **Verify against `eval.md` and report cleanly.** Output the chosen surface/taste profile, `Invariants %`, wall time, tokens/rounds if measured, and exact contract test results without skipping failed or unverified invariant IDs.
