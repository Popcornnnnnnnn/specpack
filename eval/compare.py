#!/usr/bin/env python3
"""Compare multiple SpecPack trial runs side-by-side in HTML and Markdown."""

from __future__ import annotations

import argparse
import html
import io
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from ._common import extract_criterion_ids, natural_id_key
    from .score import score_criteria_map, score_junit_report
except ImportError:
    from _common import extract_criterion_ids, natural_id_key
    from score import score_criteria_map, score_junit_report

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _discover_run_dirs(runs_dir: Path) -> list[Path]:
    dirs: list[Path] = []
    for child in sorted(runs_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / "run-meta.json").is_file() or (child / "deliverables").is_dir():
            dirs.append(child)
    return dirs


def _resolve_spec_path(runs_dir: Path, run_dirs: list[Path], explicit_spec: Optional[Path]) -> Optional[Path]:
    if explicit_spec is not None:
        return explicit_spec.resolve()
    for d in run_dirs:
        candidate = d / "pack" / "spec.md"
        if candidate.is_file():
            return candidate
    fallback = runs_dir / "spec.md"
    return fallback if fallback.is_file() else None


def _collect_run(run_dir: Path, spec_path: Optional[Path], html_dir: Path) -> dict[str, Any]:
    meta = _read_json(run_dir / "run-meta.json") or {}
    deliverables = run_dir / "deliverables"
    report = _read_json(deliverables / "run-report.json")
    junit_path = deliverables / "junit.xml"

    harness = str((report or {}).get("harness") or meta.get("harness") or "?")
    model = str((report or {}).get("model") or meta.get("model") or "?")
    surface = str((report or {}).get("surface") or "").strip()
    taste_mode = str(meta.get("taste_mode") or "?")
    tokens = (report or {}).get("tokens", "?")
    rounds = (report or {}).get("rounds", "?")

    criteria: dict[str, bool] = {}
    unverified: list[str] = []
    passed = 0
    total = int(meta.get("criteria_count") or 0)
    pct: Optional[float] = None
    status = "PENDING"

    if report and isinstance(report.get("criteria"), dict) and report["criteria"]:
        criteria = {str(k): bool(v) for k, v in report["criteria"].items()}
        unverified = [str(x) for x in report.get("unverified", [])]
        total = int(report.get("total") or len(criteria))
        passed = int(report.get("passed") or sum(1 for v in criteria.values() if v))
        pct = float(report.get("invariants_percent") or (100.0 * passed / total if total else 0.0))
        status = "PASS" if total > 0 and passed == total and not unverified else "PARTIAL"
    elif junit_path.is_file() and spec_path is not None:
        try:
            criteria, unverified = score_junit_report(junit_path, spec_path)
            summary, rc = score_criteria_map(
                criteria,
                harness=harness,
                model=model,
                surface=surface,
                tokens=tokens,
                rounds=rounds,
                unverified=unverified,
                out_stream=io.StringIO(),
            )
            if rc == 0 and summary:
                total = int(summary["total"])
                passed = int(summary["passed"])
                pct = float(summary["invariants_percent"])
                status = "PASS" if total > 0 and passed == total and not unverified else "PARTIAL"
        except (OSError, ET.ParseError, ValueError):
            status = "PENDING"

    screenshots: list[dict[str, str]] = []
    if deliverables.is_dir():
        for img in sorted(deliverables.iterdir(), key=lambda p: p.name.lower()):
            if img.is_file() and img.suffix.lower() in IMAGE_EXTENSIONS:
                rel = Path(os.path.relpath(img, html_dir)).as_posix()
                screenshots.append({"name": img.name, "rel_path": rel})

    return {
        "dir_name": run_dir.name,
        "pack": str(meta.get("pack") or "pack"),
        "harness": harness,
        "model": model,
        "surface": surface or f"({taste_mode})",
        "taste_mode": taste_mode,
        "tokens": tokens,
        "rounds": rounds,
        "status": status,
        "passed": passed,
        "total": total,
        "pct": pct,
        "criteria": criteria,
        "unverified": set(unverified),
        "screenshots": screenshots,
        "summary_md": _read_text(deliverables / "SUMMARY.md"),
        "taste_md": _read_text(deliverables / "TASTE.md"),
        "pack_gaps_md": _read_text(deliverables / "PACK_GAPS.md"),
    }


def _cell_state(run: dict[str, Any], cid: str) -> str:
    if run["status"] == "PENDING":
        return "PENDING"
    if cid in run["unverified"] or cid not in run["criteria"]:
        return "UNVERIFIED"
    return "PASS" if run["criteria"][cid] else "FAIL"


def render_markdown(runs: list[dict[str, Any]], criterion_ids: list[str], pack_name: str, generated_at: str) -> str:
    lines = [
        f"# SpecPack Comparison — {pack_name}",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Leaderboard",
        "",
        "| Run | Harness | Model | Status | Surface / Style | Invariants % | Passed | Tokens | Rounds | Screenshots |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in runs:
        pct_str = f"{r['pct']:.1f}%" if r["pct"] is not None else "—"
        passed_str = f"{r['passed']}/{r['total']}" if r["status"] != "PENDING" else f"—/{r['total'] or '?'}"
        lines.append(
            f"| `{r['dir_name']}` | `{r['harness']}` | `{r['model']}` | **{r['status']}** | "
            f"{r['surface']} | {pct_str} | {passed_str} | {r['tokens']} | {r['rounds']} | {len(r['screenshots'])} |"
        )

    if criterion_ids:
        lines.extend(["", "## Invariant Matrix", ""])
        header = "| ID | " + " | ".join(f"`{r['dir_name']}`" for r in runs) + " |"
        sep = "| --- | " + " | ".join("---" for _ in runs) + " |"
        lines.extend([header, sep])
        for cid in criterion_ids:
            row = f"| `[{cid}]` | " + " | ".join(_cell_state(r, cid) for r in runs) + " |"
            lines.append(row)

    lines.append("")
    return "\n".join(lines)


def _render_doc_details(title: str, content: str) -> str:
    if not content:
        return ""
    esc_title = html.escape(title)
    esc_body = html.escape(content)
    return f"<details><summary>{esc_title}</summary><pre>{esc_body}</pre></details>"


def render_html(runs: list[dict[str, Any]], criterion_ids: list[str], pack_name: str, generated_at: str) -> str:
    completed = sum(1 for r in runs if r["status"] != "PENDING")
    cards_html: list[str] = []

    for r in runs:
        status_cls = r["status"].lower()
        pct_text = f"{r['pct']:.1f}%" if r["pct"] is not None else "—"
        passed_text = f"{r['passed']}/{r['total']}" if r["status"] != "PENDING" else f"0/{r['total'] or '?'}"

        if r["screenshots"]:
            thumbs = "".join(
                f'<button class="thumb" type="button" data-src="{html.escape(s["rel_path"])}" '
                f'data-caption="{html.escape(r["dir_name"] + " / " + s["name"])}">'
                f'<img src="{html.escape(s["rel_path"])}" alt="{html.escape(s["name"])}" loading="lazy">'
                f"<span>{html.escape(s['name'])}</span></button>"
                for s in r["screenshots"]
            )
            gallery = f'<div class="gallery">{thumbs}</div>'
        else:
            gallery = '<div class="empty-gallery">No screenshots in <code>deliverables/</code> yet.</div>'

        details = (
            _render_doc_details("SUMMARY.md", r["summary_md"])
            + _render_doc_details("TASTE.md", r["taste_md"])
            + _render_doc_details("PACK_GAPS.md", r["pack_gaps_md"])
        )

        cards_html.append(
            f"""<article class="card">
  <header class="card-head">
    <div>
      <div class="run-id">{html.escape(r['dir_name'])}</div>
      <h2>{html.escape(r['harness'])} · <span class="muted">{html.escape(r['model'])}</span></h2>
    </div>
    <span class="badge badge-{status_cls}">{html.escape(r['status'])}</span>
  </header>
  <p class="surface"><strong>Surface:</strong> {html.escape(r['surface'])}</p>
  <dl class="metrics">
    <div><dt>Invariants</dt><dd>{html.escape(pct_text)}</dd></div>
    <div><dt>Passed</dt><dd>{html.escape(passed_text)}</dd></div>
    <div><dt>Tokens</dt><dd>{html.escape(str(r['tokens']))}</dd></div>
    <div><dt>Rounds</dt><dd>{html.escape(str(r['rounds']))}</dd></div>
  </dl>
  {gallery}
  <div class="docs">{details}</div>
</article>"""
        )

    matrix_rows: list[str] = []
    for cid in criterion_ids:
        cells = "".join(
            f'<td><span class="pill pill-{_cell_state(r, cid).lower()}">{_cell_state(r, cid)}</span></td>'
            for r in runs
        )
        matrix_rows.append(f"<tr><th><code>[{html.escape(cid)}]</code></th>{cells}</tr>")

    col_headers = "".join(f"<th>{html.escape(r['dir_name'])}</th>" for r in runs)
    matrix_section = (
        f"""<section class="matrix-section">
  <h2>Invariant Matrix</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Criterion</th>{col_headers}</tr></thead>
      <tbody>{''.join(matrix_rows)}</tbody>
    </table>
  </div>
</section>"""
        if criterion_ids
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SpecPack Comparison — {html.escape(pack_name)}</title>
  <style>
    :root {{
      --bg: #f8f9fb;
      --surface: #ffffff;
      --surface-2: #f1f3f7;
      --border: #e3e6ee;
      --text: #11141c;
      --muted: #5d6475;
      --pass-bg: #e7f6ec;
      --pass-fg: #136f38;
      --fail-bg: #fdeaea;
      --fail-fg: #b42318;
      --warn-bg: #fff4df;
      --warn-fg: #9a5b00;
      --pend-bg: #eef0f5;
      --pend-fg: #4b5565;
      --accent: #4c5fd5;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0c0e14;
        --surface: #131620;
        --surface-2: #191d2a;
        --border: #252a3a;
        --text: #eef1f7;
        --muted: #939db2;
        --pass-bg: #112d1e;
        --pass-fg: #5cd38c;
        --fail-bg: #351518;
        --fail-fg: #f87171;
        --warn-bg: #33240d;
        --warn-fg: #f5b942;
        --pend-bg: #1f2432;
        --pend-fg: #9aa4b8;
        --accent: #7c8cff;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 32px 24px 64px;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
    }}
    .wrap {{ max-width: 1320px; margin: 0 auto; }}
    .top {{
      display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline;
      gap: 12px; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px;
    }}
    .top h1 {{ margin: 0; font-size: 22px; letter-spacing: -0.02em; }}
    .sub {{ color: var(--muted); font-size: 13px; }}
    .grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 18px; margin-bottom: 32px;
    }}
    .card {{
      background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
      padding: 18px; display: flex; flex-direction: column; gap: 14px;
    }}
    .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
    .run-id {{ font: 12px/1.3 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); }}
    .card h2 {{ margin: 2px 0 0; font-size: 16px; letter-spacing: -0.01em; }}
    .muted {{ color: var(--muted); font-weight: 500; }}
    .surface {{ margin: 0; font-size: 13px; color: var(--muted); }}
    .surface strong {{ color: var(--text); font-weight: 600; }}
    .metrics {{
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
      margin: 0; padding: 10px; background: var(--surface-2); border-radius: 8px;
    }}
    .metrics dt {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
    .metrics dd {{ margin: 2px 0 0; font: 600 14px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .badge, .pill {{
      display: inline-block; padding: 3px 8px; border-radius: 999px;
      font: 600 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: 0.03em;
    }}
    .badge-pass, .pill-pass {{ background: var(--pass-bg); color: var(--pass-fg); }}
    .badge-partial, .pill-fail {{ background: var(--fail-bg); color: var(--fail-fg); }}
    .pill-unverified {{ background: var(--warn-bg); color: var(--warn-fg); }}
    .badge-pending, .pill-pending {{ background: var(--pend-bg); color: var(--pend-fg); }}
    .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }}
    .thumb {{
      appearance: none; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px;
      padding: 6px; text-align: left; color: var(--muted); cursor: pointer;
    }}
    .thumb:hover {{ border-color: var(--accent); }}
    .thumb img {{ width: 100%; height: 120px; object-fit: cover; border-radius: 5px; display: block; }}
    .thumb span {{ display: block; margin-top: 5px; font: 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .empty-gallery {{
      padding: 18px; border: 1px dashed var(--border); border-radius: 8px;
      text-align: center; color: var(--muted); font-size: 12px;
    }}
    .docs details {{ border-top: 1px solid var(--border); padding-top: 8px; margin-top: 6px; }}
    .docs summary {{ cursor: pointer; font-weight: 600; font-size: 12px; color: var(--muted); }}
    .docs pre {{
      margin: 8px 0 0; padding: 10px; background: var(--surface-2); border-radius: 8px;
      white-space: pre-wrap; word-break: break-word; font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
      max-height: 280px; overflow: auto;
    }}
    .matrix-section h2 {{ margin: 0 0 12px; font-size: 17px; }}
    .table-wrap {{
      background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow-x: auto;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); text-align: left; }}
    thead th {{ font-size: 12px; color: var(--muted); background: var(--surface-2); }}
    tbody tr:last-child th, tbody tr:last-child td {{ border-bottom: none; }}
    dialog#lightbox {{
      padding: 0; border: 1px solid var(--border); border-radius: 12px; background: var(--surface);
      color: var(--text); max-width: 92vw; max-height: 92vh;
    }}
    dialog#lightbox::backdrop {{ background: rgba(0, 0, 0, 0.72); }}
    .lb-body {{ padding: 12px; display: flex; flex-direction: column; gap: 8px; }}
    .lb-body img {{ max-width: 88vw; max-height: 80vh; object-fit: contain; border-radius: 6px; }}
    .lb-bar {{ display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--muted); }}
    .lb-close {{
      border: 1px solid var(--border); background: var(--surface-2); color: var(--text);
      border-radius: 6px; padding: 4px 10px; cursor: pointer;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="top">
      <div>
        <h1>SpecPack Side-by-Side Comparison — {html.escape(pack_name)}</h1>
        <div class="sub">{completed}/{len(runs)} runs scored · {len(criterion_ids)} core invariants · generated {html.escape(generated_at)}</div>
      </div>
    </header>
    <section class="grid">{''.join(cards_html)}</section>
    {matrix_section}
  </div>
  <dialog id="lightbox">
    <div class="lb-body">
      <div class="lb-bar"><span id="lb-caption"></span><button class="lb-close" id="lb-close" type="button">Close</button></div>
      <img id="lb-img" src="" alt="">
    </div>
  </dialog>
  <script>
    const dlg = document.getElementById('lightbox');
    const lbImg = document.getElementById('lb-img');
    const lbCap = document.getElementById('lb-caption');
    document.querySelectorAll('.thumb').forEach((btn) => {{
      btn.addEventListener('click', () => {{
        lbImg.src = btn.dataset.src || '';
        lbCap.textContent = btn.dataset.caption || '';
        dlg.showModal();
      }});
    }});
    document.getElementById('lb-close').addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', (e) => {{ if (e.target === dlg) dlg.close(); }});
  </script>
</body>
</html>
"""


def compare_runs(
    runs_dir: Path,
    *,
    spec_path: Optional[Path] = None,
    html_out: Optional[Path] = None,
    md_out: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Scan run subdirectories and write comparison.html + COMPARISON.md."""
    runs_dir = runs_dir.resolve()
    if not runs_dir.is_dir():
        raise FileNotFoundError(f"Runs directory does not exist: {runs_dir}")

    run_dirs = _discover_run_dirs(runs_dir)
    if not run_dirs:
        raise ValueError(f"No trial run directories found in {runs_dir}")

    resolved_spec = _resolve_spec_path(runs_dir, run_dirs, spec_path)
    criterion_ids: list[str] = []
    if resolved_spec is not None and resolved_spec.is_file():
        criterion_ids, _ = extract_criterion_ids(resolved_spec)
        criterion_ids.sort(key=natural_id_key)

    html_target = (html_out or (runs_dir / "comparison.html")).resolve()
    md_target = (md_out or (runs_dir / "COMPARISON.md")).resolve()
    html_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.parent.mkdir(parents=True, exist_ok=True)

    runs = [_collect_run(d, resolved_spec, html_target.parent) for d in run_dirs]
    if not criterion_ids:
        seen = set()
        for r in runs:
            seen.update(r["criteria"].keys())
        criterion_ids = sorted(seen, key=natural_id_key)

    pack_name = next((r["pack"] for r in runs if r["pack"] and r["pack"] != "pack"), runs[0]["pack"])
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    html_target.write_text(render_html(runs, criterion_ids, pack_name, generated_at), encoding="utf-8")
    md_target.write_text(render_markdown(runs, criterion_ids, pack_name, generated_at), encoding="utf-8")
    return html_target, md_target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate side-by-side comparison.html and COMPARISON.md from SpecPack trial runs."
    )
    parser.add_argument("runs_dir", type=Path, help="Parent directory containing trial run subdirectories.")
    parser.add_argument("--spec", type=Path, default=None, help="Optional path to spec.md.")
    parser.add_argument("--html-out", type=Path, default=None, help="Output HTML path (default: <runs_dir>/comparison.html).")
    parser.add_argument("--md-out", type=Path, default=None, help="Output Markdown path (default: <runs_dir>/COMPARISON.md).")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        html_path, md_path = compare_runs(
            args.runs_dir,
            spec_path=args.spec,
            html_out=args.html_out,
            md_out=args.md_out,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {html_path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
