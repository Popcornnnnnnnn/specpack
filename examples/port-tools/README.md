# Port Tools — SpecPack Reference Pack (v0.2)

First complete SpecPack **v0.2** reference pack, harvested from a real desktop utility into a cross-platform, surface-agnostic contract.

**Port Tools** turns raw local TCP ports into calm workspace awareness:
1. Know what is listening across IPv4/IPv6 without port blind spots.
2. See which Git repo, branch, worktree, or Docker container owns each port.
3. Give dev servers stable `http://{alias}.localhost` URLs with zero `/etc/hosts` or root CA setup.
4. Review impact safely before stopping any process, without killing Docker or shared runtimes.

Because the pack locks behavior and safety invariants instead of framework or pixel layout, rebuilding agents use its `/grill-me`-style **Guided Taste Interview** (`SKILL.md`) to tailor the surface (macOS menu bar / system tray, local web dashboard, TUI, or command launcher), mental model, and visual vibe to each user.

## Contents

- [pack.yaml](pack.yaml) — pack metadata and rebuild budgets (`12` core invariants)
- [SKILL.md](SKILL.md) — freedom rules + `/grill-me`-style **Guided Taste Interview**
- [spec.md](spec.md) — the locked contract: `Non-goals` + `Core invariants` (`[1.1]`–`[4.3]`)
- [decisions.md](decisions.md) — advisory reference architecture, dead ends, and taste calls
- [reference/](reference/README.md) — light & dark macOS menu bar moodboard screenshots *(inspiration only)*
- [examples/scenarios.json](examples/scenarios.json) — synthetic multi-worktree, proxy, Docker, and stop-safety scenarios
- [tests/contract_harness.py](tests/contract_harness.py) — stdlib contract verifier + live local fixtures emitting JUnit XML
- [eval.md](eval.md) — validation, contract test, and scoring commands

## Quick check

```bash
python3 ../../eval/validate.py . --strict
python3 tests/contract_harness.py --self-test
```
