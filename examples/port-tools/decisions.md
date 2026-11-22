# Port Tools — Decisions, Dead Ends & Taste Calls (Advisory)

Everything in this file records lessons learned from building Port Tools once natively (`SwiftUI` menu bar app + `Go` core). None of it is mandatory for your rebuild — pick simpler or different parts whenever they fit your chosen surface and OS better.

## Reference choices (advisory)

- **Split UI + headless engine (reference macOS build):**
  - Thin `SwiftUI MenuBarExtra` desktop client talking over a `0600` local Unix domain socket to a bundled `Go` engine hosting discovery, `git` resolution, route persistence, `httputil.ReverseProxy`, and safe stop validation.
  - Works well when you want native macOS UI craft plus Go's rock-solid `net/http/httputil.ReverseProxy` and WebSocket hijacking.
- **Alternative single-stack options worth considering:**
  - **Cross-platform Web Dashboard:** Single `Go` or `Rust` (`axum`/`hyper`) or `Node`/`Bun` binary serving the loopback dashboard API/UI and the `*.localhost` proxy together — zero IPC hop and works identically on macOS, Linux, and WSL.
  - **Terminal TUI:** `Go` (`bubbletea`) or `Rust` (`ratatui`) talking directly to live OS inspection and running the proxy in-process.
  - **Launcher / Hotkey workflow:** Headless local daemon exposing fast JSON commands (`scan`, `alias`, `stop-plan`, `stop`) wired into Raycast, Alfred, or a minimal quick-open window.
- **OS socket inspection options:**
  - macOS: `lsof -nP -iTCP -sTCP:LISTEN -F pcLnu` (or `libproc` bindings) + `ps` start-time/ppid/cpu metadata.
  - Linux: `ss -tlnpH` or `/proc/net/tcp{,6}` + `/proc/{pid}/{cmdline,cwd,stat}`.
  - Windows: IP Helper `GetExtendedTcpTable` / PowerShell `Get-NetTCPConnection`.

## Dead ends & traps

- **Climbing interpreter or package-manager directories during Git discovery:**
  - *Trap:* Inspecting a listener's open files or cwd and running `git rev-parse` blindly matches parent tool/cache checkouts (e.g. Homebrew Cellar/tap repos, `.venv/lib/python.../site-packages`, `node_modules`, `.rustup`, `.nvm`, `cargo/registry`) and attributes `python3` or `node` to someone else's repo.
  - *Avoid:* Apply an explicit non-project directory filter *before* running Git root lookup, and ignore binary/runtime package stores cleanly.
- **Parsing `.git/HEAD` directly instead of calling `git`:**
  - *Trap:* Linked `git worktree` checkouts store a `.git` *file* (`gitdir: /path/to/.git/worktrees/{branch}`) rather than a directory. Ad-hoc parsers fail on worktrees or collapse multiple worktrees into one common repo bucket.
  - *Avoid:* Query `git rev-parse --show-toplevel`, `--git-common-dir`, `--abbrev-ref HEAD`, and `git config --get remote.origin.url` with short bounded timeouts from the resolved project cwd, keying workspace buckets by distinct top-level checkout path. Always strip embedded `user:pass@` credentials from remote URLs.
- **Promoting Swagger UI or Chrome DevTools ports to primary Web apps:**
  - *Trap:* Any endpoint answering `200 OK` on `/` looks "HTTP-capable", flooding the workspace with FastAPI `/docs` stubs, OpenAPI JSON endpoints, metrics servers, and Chromium `--remote-debugging-port` listeners.
  - *Avoid:* Inspect response content-type and light body signatures under a tight byte cap; separate pure APIs, Swagger/OpenAPI, and DevTools HTTP ports cleanly from directly openable HTML Web UIs, and corroborate with project context before promoting to primary workspace cards.
- **Assumed `127.0.0.1` upstream target breaking IPv6-only listeners:**
  - *Trap:* Vite, Django, or Python `http.server` bound to `localhost` frequently listen only on `[::1]`. Forwarding `foo.localhost` blindly to `127.0.0.1:{port}` fails with connection refused while the app is alive.
  - *Avoid:* Record each listener's actual bound IP family and dial `[::1]:{port}` when loopback is IPv6-only (or try the resolved loopback endpoints cleanly).
- **HTTP keep-alive from the built-in proxy holding sockets after `SIGTERM`:**
  - *Trap:* Idle pooled connections inside the reverse proxy or active SSE streams can delay port cleanup or leave connections open while checking whether the upstream port actually closed.
  - *Avoid:* Disable HTTP connection reuse for diagnostic probes (`DisableKeepAlives`) and close/reset idle proxy transport pools for the target upstream when verifying graceful stop completion.
- **Root CA trust stores and Caddy auto-HTTPS leaks:**
  - *Trap:* Emulating `Portless`-style root CA installation or running `Caddy` with automatic TLS triggers OS keychain/admin prompts, leaks background cert/state files on uninstall, and conflicts with user expectations for instant local dev URLs.
  - *Avoid:* Default strictly to unprivileged loopback `http://{alias}.localhost:{proxy-port}` (`127.0.0.1` / `[::1]`). Even if adding an optional macOS `launchd` port-80 forwarder helper later, strictly restrict the forwarder to loopback connections carrying normalized `*.localhost` `Host` headers and refuse non-`.localhost` traffic (`421`).
- **Silently wiping corrupt route JSON on startup:**
  - *Trap:* Truncated JSON after crash/sleep causes naive `os.Remove` recovery and silently deletes every custom user alias.
  - *Avoid:* Write route files atomically (`write temp + fsync + rename`), and if loading fails, rename the unreadable file to a timestamped `.corrupt-*` backup first so aliases are recoverable.
- **Stopping solely by PID without identity revalidation:**
  - *Trap:* Between showing a confirmation modal and clicking Stop, a crashed process's PID can be recycled by an unrelated process.
  - *Avoid:* Issue a single-use, short-lived `plan_token` bound to `(pid, command/exe, process_start_time, listening_ports)` and revalidate all fields immediately before sending `SIGTERM`.

## Taste calls

- **Three mental models worth honoring (pick what matches Q2):**
  - *Project-first (reference default):* Groups servers cleanly under repo + branch/worktree headers (`interface-light.png` / `interface-dark.png`), matching how developers think when switching tasks.
  - *Attention-first:* Elevates `possibly forgotten` idle servers and port/alias collisions to a compact top triage zone for users who want cleanup first.
  - *Search-first:* Flattens everything into one keystroke-navigable list for launcher power users.
- **Calm defaults over configuration sprawl:** Keep secondary endpoints (`Other Web endpoints`, `Other listeners`) collapsed on first launch rather than forcing users to configure ignore lists before seeing clean project servers.
- **Inline immediacy:** Let users open `http://{alias}.localhost...` in one click and rename an alias inline without navigating through nested inspector sub-views.
