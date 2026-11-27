#!/usr/bin/env python3
"""Prepare an isolated, clean-room SpecPack trial directory and optional cloud zip bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from .validate import _parse_pack_yaml, validate_pack
except ImportError:
    from validate import _parse_pack_yaml, validate_pack

EVAL_DIR = Path(__file__).resolve().parent
IGNORE_NAMES = {"__pycache__", ".DS_Store"}
IGNORE_SUFFIXES = (".pyc", ".pyo")

DEFAULT_GITIGNORE = """__pycache__/
*.py[cod]
node_modules/
.venv/
venv/
target/
dist/
build/
.DS_Store
"""


def _copy_filtered_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree excluding Python caches and OS metadata."""

    def ignore(_dirpath: str, entries: list[str]) -> set[str]:
        ignored: set[str] = set()
        for entry in entries:
            if entry in IGNORE_NAMES or entry.endswith(IGNORE_SUFFIXES):
                ignored.add(entry)
        return ignored

    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)


def _render_operating_mode(taste_mode: str) -> str:
    if taste_mode == "interactive":
        return """## Operating Mode — Interview First, Then Build End-to-End
- **Phase 1 — Guided Taste Interview:** Start by exploring the open taste dimensions in `pack/SKILL.md` with the user using an adaptive `/grill-me`-style conversation (**one short high-level product/UX question at a time**, adapting follow-ups naturally to earlier replies, offering concise choices with a `(Recommended)` option, honoring `"just use defaults"`, stopping early once clear, and zero low-level plumbing questions). Record the chosen taste profile in `deliverables/TASTE.md`.
- **Phase 2 — Autonomous Build & Verify:** Once the interview finishes (or the human delegates defaults), proceed autonomously end-to-end without pausing for confirmations until `app/`, `contract_harness.py`, `eval/score.py`, real UI screenshots, and `deliverables/SUMMARY.md` are complete.
- **CLEAN-ROOM BOUNDARY:** Work strictly inside this trial directory (`pack/`, `eval/`, `app/`, `deliverables/`). Never read parent or sibling directories on disk.
- If anything in the pack is ambiguous, make a well-reasoned choice, document it in `deliverables/PACK_GAPS.md`, and keep moving.
- **Sandbox fallback:** If your execution environment blocks live local sockets or process inspection, complete all application code, unit tests, and read-only verification honestly (do not fabricate passing scores), and provide a one-command `app/scripts/verify.sh` for host verification."""

    return """## Operating Mode — DO NOT INTERRUPT ME
- Work autonomously end-to-end without pausing for clarification or confirmation.
- **CLEAN-ROOM BOUNDARY:** Work strictly inside this trial directory (`pack/`, `eval/`, `app/`, `deliverables/`). Never read parent or sibling directories on disk.
- If anything in the pack is ambiguous, make a well-reasoned choice, document it in `deliverables/PACK_GAPS.md`, and keep moving."""


def _render_taste_section(taste_mode: str) -> str:
    if taste_mode == "interactive":
        return """- **DO NOT skip the interview.** Before designing or writing code, explore the open taste dimensions in `pack/SKILL.md` adaptively with the user — one question at a time (never recite a rigid fixed script).
- Wait for the user's answer after each question (or adopt sensible `(Recommended)` defaults immediately if they say `"just use defaults"`), and stop once the product shape is clear.
- Write the chosen taste profile into `deliverables/TASTE.md`, then immediately execute Phase 2 end-to-end."""

    if taste_mode == "web-dashboard":
        return """- Skip the interactive pause in `pack/SKILL.md` and follow this fixed Taste Profile:
  - **Surface & form factor:** Local Web Dashboard (works cleanly on this OS)
  - **Mental model:** Project-first (Recommended)
  - **Visual vibe & density:** Crisp Linear minimal (Recommended)
  - **Local URL style:** Zero-setup `http://{alias}.localhost:{port}` (Recommended)
  - **Extras:** Keep it clean and focused (Recommended)
- Save a concise copy of these choices in `deliverables/TASTE.md`."""

    if taste_mode == "defaults":
        return """- Skip the interactive pause in `pack/SKILL.md` and adopt the `(Recommended)` defaults across the open taste dimensions in `pack/SKILL.md`.
- If running on Linux or a headless sandbox without macOS desktop GUI support, use **Local Web Dashboard** as your fallback surface so everything builds, runs live, and can be screenshot-verified.
- Record the applied defaults in `deliverables/TASTE.md`."""

    return """- Skip the interactive pause in `pack/SKILL.md` and choose your own taste profile across the open taste dimensions in `pack/SKILL.md`:
  - Pick the **best runnable surface** that compiles, runs live, passes `pack/tests/contract_harness.py`, and captures real screenshots on this OS (for Linux sandboxes, choose **Local Web Dashboard** or **Terminal TUI**; on macOS you may pick **Menu Bar App**, **Local Web Dashboard**, or **Terminal TUI**).
  - Pick your own **mental model** (Project-first, Attention-first, or Search-first), **interaction/visual feel**, and **workflow extras** matching `pack/SKILL.md`.
- Record your choices and brief taste reasoning in `deliverables/TASTE.md`."""


def _render_handoff_prompt(
    *,
    pack_name: str,
    harness: str,
    model: str,
    taste_mode: str,
    criteria_count: int,
) -> str:
    operating_block = _render_operating_mode(taste_mode)
    taste_block = _render_taste_section(taste_mode)
    return f"""# SpecPack Clean-Room Rebuild Handoff — `{pack_name}`

You are rebuilding **`{pack_name}`** strictly from the self-contained SpecPack in `pack/` (`{criteria_count}` Core Invariants).

{operating_block}

## Personalisation Brief (`taste_mode: {taste_mode}`)
{taste_block}

## Core Engineering Rules
1. Read `pack/SKILL.md`, `pack/spec.md`, `pack/decisions.md`, `pack/examples/`, `pack/reference/`, and `pack/eval.md`.
2. Obey every bracketed invariant (`[X.Y]`) and `## Non-goals` in `pack/spec.md` strictly. Treat `pack/decisions.md` and `pack/reference/` only as advice and visual inspiration.
3. Build your complete runnable implementation inside `app/`.
4. Implement the tiny CLI adapter described by `python3 pack/tests/contract_harness.py --show-contract` so the contract harness can score your implementation automatically.

## Definition of Done (complete all steps before finishing)
1. Run the contract harness and emit JUnit XML:
   ```bash
   python3 pack/tests/contract_harness.py --adapter "<your adapter command>" --junit-out deliverables/junit.xml
   ```
2. Score your JUnit output against `pack/spec.md`:
   ```bash
   python3 eval/score.py \\
     --junit deliverables/junit.xml \\
     --spec pack/spec.md \\
     --harness "{harness}" \\
     --model "{model}" \\
     --surface "<your chosen surface & visual style>" \\
     --tokens "<total tokens if known, else ?>" \\
     --rounds "<rounds if known, else ?>" \\
     --json-out deliverables/run-report.json
   ```
3. Launch your built app against real local test traffic and save **1–2 real screenshots** of the running UI (for example `deliverables/screen-1.png` and `deliverables/screen-2.png`; for a TUI, render a clean high-contrast terminal capture PNG).
4. Write `deliverables/SUMMARY.md` recording:
   - Chosen surface, mental model, visual vibe, and tech stack
   - Exact build and run commands inside `app/`
   - Wall time, token/round stats (if available), and `Invariants %`
   - Any failed/unverified invariant IDs and any pack gaps recorded in `deliverables/PACK_GAPS.md`.

Iterate until `Invariants %` reaches `100%` (or document any genuine host blocker honestly in `deliverables/SUMMARY.md`).
"""


def _init_git_repo(out_dir: Path) -> None:
    """Create a standalone clean git repository inside out_dir so agents stay sandboxed."""
    base = ["git", "-C", str(out_dir)]
    subprocess.run([*base, "init", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run([*base, "add", "-A"], check=True, capture_output=True, text=True)
    subprocess.run(
        [
            *base,
            "-c",
            "user.name=SpecPack Trial",
            "-c",
            "user.email=trial@specpack.invalid",
            "commit",
            "-m",
            "Initialize clean-room SpecPack trial",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_zip_bundle(out_dir: Path, zip_out: Path) -> None:
    """Package out_dir into a portable zip excluding .git metadata."""
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(out_dir.rglob("*")):
            rel = path.relative_to(out_dir)
            if ".git" in rel.parts or path.name in IGNORE_NAMES or path.suffix in IGNORE_SUFFIXES:
                continue
            if path.is_file():
                zf.write(path, arcname=rel.as_posix())


def prepare_trial(
    *,
    pack_dir: Path,
    out_dir: Path,
    harness: str,
    model: str,
    taste_mode: str = "interactive",
    git_init: bool = False,
    zip_out: Optional[Path] = None,
) -> dict[str, object]:
    """Create an isolated clean-room trial directory and return run metadata."""
    pack_dir = pack_dir.resolve()
    out_dir = out_dir.resolve()

    errors, _, criteria_count = validate_pack(pack_dir)
    if errors:
        raise ValueError("Invalid pack:\n" + "\n".join(errors))
    if criteria_count == 0:
        raise ValueError(f"No bracketed criteria found in {pack_dir / 'spec.md'}")

    if out_dir.is_relative_to(pack_dir):
        raise ValueError("--out must be outside the source pack.")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"Destination directory already exists and is non-empty: {out_dir}")
    if zip_out is not None:
        zip_out = zip_out.resolve()
        if zip_out.is_relative_to(out_dir):
            raise ValueError("--zip-out must be outside --out.")

    top_meta, _ = _parse_pack_yaml(pack_dir / "pack.yaml")
    pack_name = top_meta.get("name") or pack_dir.name
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_meta = {
        "pack": pack_name,
        "harness": harness,
        "model": model,
        "taste_mode": taste_mode,
        "created_at": created_at,
        "criteria_count": criteria_count,
    }

    prompt_text = _render_handoff_prompt(
        pack_name=pack_name,
        harness=harness,
        model=model,
        taste_mode=taste_mode,
        criteria_count=criteria_count,
    )
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".specpack-", dir=out_dir.parent) as staging:
        staged_run = Path(staging) / "run"
        _copy_filtered_tree(pack_dir, staged_run / "pack")
        _copy_filtered_tree(EVAL_DIR, staged_run / "eval")

        for subdir in ("app", "deliverables"):
            d = staged_run / subdir
            d.mkdir()
            (d / ".gitkeep").write_text("", encoding="utf-8")

        (staged_run / ".gitignore").write_text(DEFAULT_GITIGNORE, encoding="utf-8")
        (staged_run / "run-meta.json").write_text(json.dumps(run_meta, indent=2) + "\n", encoding="utf-8")
        (staged_run / "HANDOFF_PROMPT.md").write_text(prompt_text, encoding="utf-8")

        if git_init:
            _init_git_repo(staged_run)

        if zip_out is None:
            staged_run.rename(out_dir)
        else:
            zip_out.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".specpack-", dir=zip_out.parent) as bundle_staging:
                staged_zip = Path(bundle_staging) / "bundle.zip"
                _write_zip_bundle(staged_run, staged_zip)
                staged_run.rename(out_dir)
                try:
                    staged_zip.replace(zip_out)
                except OSError:
                    out_dir.rename(staged_run)
                    raise

    return run_meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold a clean-room SpecPack trial folder and optional cloud bundle zip."
    )
    parser.add_argument("--pack", type=Path, required=True, help="Path to source SpecPack directory.")
    parser.add_argument("--out", type=Path, required=True, help="Output isolated trial directory.")
    parser.add_argument("--harness", required=True, help="Target agent harness identifier.")
    parser.add_argument("--model", required=True, help="Target model identifier.")
    parser.add_argument(
        "--taste-mode",
        choices=("interactive", "free", "web-dashboard", "defaults"),
        default="interactive",
        help="Personalisation prompt mode written to HANDOFF_PROMPT.md (default: interactive).",
    )
    parser.add_argument(
        "--git-init",
        action="store_true",
        help="Initialize an isolated git repo and commit the scaffold inside --out.",
    )
    parser.add_argument(
        "--zip-out",
        type=Path,
        default=None,
        help="Optional zip output path (excludes .git) for cloud agent upload.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        meta = prepare_trial(
            pack_dir=args.pack,
            out_dir=args.out,
            harness=args.harness,
            model=args.model,
            taste_mode=args.taste_mode,
            git_init=args.git_init,
            zip_out=args.zip_out,
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Prepared trial: {args.out} "
        f"(pack={meta['pack']}, harness={meta['harness']}, model={meta['model']}, "
        f"taste={meta['taste_mode']}, criteria={meta['criteria_count']})"
    )
    if args.zip_out is not None:
        print(f"Cloud zip:      {args.zip_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
