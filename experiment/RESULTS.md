# Rebuild Results

| # | Date | Pack | Harness | Model | Surface / Style | Wall time | Convs/Rounds | Tokens | Invariants % | Failed criteria | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-11-23 | `port-tools` | `aws-quick` | `claude-opus` | Local Web Dashboard · Project-first · Crisp Linear minimal (Light/Dark) | 17s verify | ? | ? | 100.0% (12/12) | none | Python 3 stdlib; authored remotely without local runner, verified unmodified on macOS host (`11/11` unit tests + `12/12` harness). Score: 90/100. |
| 2 | 2026-11-23 | `port-tools` | `chatgpt-codex` | `codex` | Local Web Dashboard + Terminal Inspector · Project-first dark minimal | 6m 20s | 1 | ? | 66.7% (8/12) | 1.3, 2.2, 4.2, 4.3 | Go + `libproc`/`lsof`; reported `0/12` honestly inside socket-blocked sandbox with TUI captures; `8/12` unrestricted (`project.go` `/var` symlink/ceiling attribution bug). #1 Taste/Craft (`24/25`); Score: 78/100. |
| 3 | 2026-11-23 | `port-tools` | `command-code` | `deepseek` | Local Web Dashboard · Project-first · Crisp Linear minimal light + modal | 24m 51s | 1 | ? | 100.0% (12/12) | none | Python 3 stdlib; full autonomous execution + headless Chrome Retina captures + out-of-harness tests; independently re-verified `12/12`. Score: 91/100. |
