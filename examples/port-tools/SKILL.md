---
name: port-tools
description: Build your own Port Tools — live local-port discovery, Git/worktree attribution, locked *.localhost reverse proxy, and safe two-step stop review — tailored via a lightweight Guided Taste Interview.
---

# How to build Port Tools (Freedom by Default)

1. **Obey `spec.md` strictly.** Its `## Non-goals` and 12 bracketed Core Invariants (`[1.1]`–`[4.3]`) are the only locked contract. In particular, `{alias}.localhost` reverse proxying is part of the core product contract, not an optional extra.
2. **Read `decisions.md` as field notes, not orders.** Reuse what helps your chosen stack and OS; avoid the documented dead ends and traps. Nothing locks you into macOS, SwiftUI, Go, or a menu bar popover unless the user wants that.
3. **Run the Personalisation Interview (`Guided Taste Interview`) before designing or writing code.**
   Think of this like a lightweight `/grill-me` focused solely on **product shape and user taste**:
   - **Ask one question at a time** in plain language and wait for the user's answer before moving on.
   - **Give 2–4 concise choices per question** and mark one `(Recommended)`.
   - **Honor `"just use defaults"`** at any point: immediately adopt all remaining `(Recommended)` defaults, summarize them briefly, and proceed.
   - **Branch dynamically:** skip follow-ups made irrelevant by earlier answers (for instance, skip GUI styling/density when the user chooses a TUI or command launcher).
   - **Zero plumbing questions:** never ask the user about IPC sockets, programming languages, polling intervals, schemas, or OS syscall flags unless they explicitly bring them up — make clean internal engineering choices yourself.

   Walk through these questions one at a time:

   - **Question 1 — Where should Port Tools live? (Surface & form factor)**
     - `A` *(Recommended on desktop)*: **Menu bar / system tray popover** — always one click away without taking a permanent window or browser tab.
     - `B`: **Local Web dashboard** — opens in any browser across macOS, Linux, and Windows; ideal for split-screen monitoring.
     - `C`: **Keyboard-first Terminal TUI** — stays inside a terminal pane with fast key navigation.
     - `D`: **Command launcher / CLI + hotkey integration** (e.g. Raycast, Alfred, or quick palette) — invisible until summoned.

   - **Question 2 — How should running listeners be organized by default? (Mental model)**
     - `A` *(Recommended)*: **Project-first** — group servers by Git repository, branch, and worktree, with non-dev endpoints tucked under collapsed secondary sections.
     - `B`: **Attention-first** — pin `possibly forgotten` servers, port collisions, and stop candidates at the top like a triage inbox.
     - `C`: **Search-first** — one fast, filterable flat list sorted by relevance and recent activity.

   - **Question 3 — What visual vibe and density feel right?** *(Skip automatically if Question 1 was `C` Terminal TUI or headless `D` launcher)*
     - `A` *(Recommended)*: **Crisp Linear minimal** — disciplined monochrome palette, razor-thin borders, tabular monospace ports and `.localhost` URLs.
     - `B`: **Quiet native** — blends smoothly into host OS chrome, subtle translucency, gentle status accents.
     - `C`: **Dense developer table** — compact rows putting port, bind scope, branch, alias, and idle age side-by-side in one scan.

   - **Question 4 — How should `{alias}.localhost` URLs look?**
     - `A` *(Recommended)*: **Zero-setup `http://{alias}.localhost:{port}` everywhere** — starts instantly with unprivileged loopback routing and zero OS setup prompts.
     - `B`: **Port-free `http://{alias}.localhost` when available** — add an optional local port-80 forwarder where the OS supports it cleanly, while always keeping `http://{alias}.localhost:{port}` working automatically as fallback.

   - **Question 5 — Any personal workflow touches to include?**
     - `A` *(Recommended)*: **Keep it clean and focused** — discover ports, click to open `{alias}.localhost`, copy URL/port, edit alias, safe stop review.
     - `B`: **Power workflow extras** — pick any combination: global search hotkey, copy URL on primary click, jump to project folder / Git remote, or auto-collapse noisy desktop helper apps.

4. **Glance at `reference/` strictly as a moodboard.** The screenshots show one macOS author's light/dark menu bar aesthetic — never treat them as a pixel target or platform restriction.
5. **Verify against `eval.md` and report cleanly.** Output the chosen surface/taste profile, `Invariants %`, wall time, tokens/rounds if measured, and exact contract test results without skipping failed or unverified invariant IDs.
