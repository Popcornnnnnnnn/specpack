# Port Tools — Core Contract (`spec.md`)

Port Tools turns raw OS TCP listeners into quiet workspace awareness: **live local discovery**, **project/worktree/container attribution**, **stable loopback `*.localhost` aliases**, and **conservative two-step stop safety**.

Everything in `decisions.md` and `reference/` is advisory. Everything below is **strict contract**.

## Non-goals

- **No public tunnels or LAN/WAN sharing:** Do not build ngrok-style public URLs, relay servers, or cross-machine port exposure.
- **No accounts, telemetry, or cloud sync:** Run 100% locally with zero login gates or phone-home analytics.
- **No invasive host networking edits by default:** Never modify `/etc/hosts`, never install trusted root CA certificates into system/browser stores, and never terminate HTTPS with synthetic CAs by default.
- **No auto-killing servers:** Never kill idle, old, or detached listeners automatically without explicit human confirmation.
- **No generic container or init replacement:** Do not try to replace Docker Desktop, Compose, `launchd`, or `systemd`.
- **No traffic or secret hoarding:** Do not capture HTTP request/response bodies, cookies, auth headers, or raw remote Git credentials.

## Core invariants

### 1. Accurate Local Listener Discovery & Web Classification

- [1.1] **Complete current-user IPv4/IPv6 discovery with bind clarity:** Discover all listening TCP sockets owned by the current user across all ports (zero hardcoded dev-port blind spots). Record numeric PID, command/executable, bound IP/family (`127.0.0.1`, `[::1]`, `0.0.0.0`, `[::]`, or interface address), and bind scope (`loopback` vs `LAN / all interfaces`). Surface inspection errors explicitly instead of silently showing an empty port list.
- [1.2] **Bounded active probing distinguishing openable Web pages from APIs and raw TCP:** Probe loopback-reachable listeners using strict concurrency and response-size caps (limited redirects, bounded header/body peek) to classify: (a) directly openable HTML Web UIs/apps, (b) non-HTML HTTP services such as JSON APIs, Swagger/OpenAPI docs, or Chrome DevTools HTTP debuggers, and (c) raw non-HTTP TCP listeners. Do not present Swagger/OpenAPI endpoints or browser debug ports as primary openable Web apps.
- [1.3] **Conservative promotion to primary developer apps:** Promote a listener into primary app/project workspace groups only with corroborated project attribution or clear developer-runtime evidence; retain uncorroborated HTTP endpoints and desktop/background services in distinct secondary sections (`Other Web endpoints` / `Other listeners`) so noise stays low without hiding real ports.

### 2. Project Attribution, Worktree Isolation & Container Awareness

- [2.1] **Safe Git/manifest attribution without false package-manager roots:** Resolve listener working directories or main project entry files to the owning Git root, active branch, credential-free remote identifier (strip any `username:token@` or embedded credentials before storage or display), and nearest manifest/app name (`package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, etc.), while explicitly refusing to climb into toolchain or dependency directories (`node_modules`, `site-packages`, virtualenvs, Homebrew/package-manager caches, Rust/Go toolchains).
- [2.2] **Distinct Git worktree identity:** Keep listeners running inside separate Git worktrees of the same repository visually and logically separate using each worktree's checkout path, branch, and app metadata rather than collapsing them under one ambiguous project entry.
- [2.3] **Container-published listener awareness:** Identify host-published Docker/container-forwarded ports and attach container/image/published-port metadata rather than misattributing the container daemon as the developer app.

### 3. Locked Loopback `*.localhost` Reverse Proxy

- [3.1] **Zero-setup loopback reverse proxy across HTTP, upgrades, and IPv6:** Run a loopback-only (`127.0.0.1` / `[::1]`) reverse proxy routing `{alias}.localhost` Host headers (case-insensitive, port-normalized) to registered upstreams — supporting standard HTTP, WebSocket/HMR upgrades, SSE, streaming responses, and IPv6-only (`[::1]`) upstreams — without touching `/etc/hosts` or installing root CAs by default. Expose unprivileged `http://{alias}.localhost:{proxy-port}` reliably everywhere; if optional port-free `http://{alias}.localhost` forwarding is unavailable or disabled, visibly keep `http://{alias}.localhost:{proxy-port}` active as fallback.
- [3.2] **Logical route persistence and collision refusal:** Rebind persisted aliases automatically when a known project/worktree/app restarts on a new PID or ephemeral port using logical app/worktree identity (not raw PID), normalize alias labels cleanly to valid DNS host labels, and reject silent alias collisions between two distinct apps or worktrees.
- [3.3] **Helpful offline route diagnostics and corrupt-state preservation:** Return a clear, identifiable missing-upstream response (`502` / friendly offline message naming the alias and state) rather than a blank proxy failure when an aliased app is stopped; if persisted route storage fails validation or JSON parsing, preserve a timestamped `.corrupt-*` backup on disk before recovering so saved aliases are never silently wiped.

### 4. Conservative Staleness & Two-Step Safe Stop

- [4.1] **Evidence-backed `possibly forgotten` hint with zero auto-kill:** Flag a dev listener as `possibly forgotten` only when conservative signals agree (e.g. sustained process-tree/CPU inactivity paired with lost editor/terminal context where observable and meaningful idle age), display the observed reason/evidence, never use the ambiguous label `unused`, never trigger purely on detached PPID=1 or age alone, and never kill processes automatically.
- [4.2] **Pre-stop impact review, hard exclusions, and atomic identity revalidation:** Stopping a listener must first generate a short-lived impact plan displaying target PID, port(s), project/worktree, and routed alias(es), and MUST refuse Docker-published services (advising stopping the container instead), shared/system runtimes (`dockerd`, `launchd`, `systemd`, container helpers, self-process), other-user listeners, and unattributed critical processes. Immediately before issuing `SIGTERM`, atomically revalidate the single-use stop token against the live PID's executable/command, start identity, and listening port(s) to defeat PID reuse.
- [4.3] **Verified port release and explicit escalation to force stop:** After sending `SIGTERM`, wait cleanly and verify the target socket(s) actually disappear before reporting stopped; only after graceful stop times out may the user invoke `SIGKILL` through a separate explicit second confirmation.

## Measurable success

- `Invariants % = 100` (`12/12` scenarios passing in `eval/score.py` against `tests/contract_harness.py`).
- Fresh local startup reaches working discovery + `{alias}.localhost` HTTP & WebSocket proxying in under `5s` with zero root prompts, zero `/etc/hosts` edits, and zero CA trust changes.
- `100%` of Docker-owned ports, shared runtimes, and stale mismatched stop tokens are refused safely in stop execution tests.
