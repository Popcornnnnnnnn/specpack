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
    from ._common import natural_id_key
    from .score import read_run_report, read_scoring_spec, score_criteria_map, score_junit_criteria
except ImportError:
    from _common import natural_id_key
    from score import read_run_report, read_scoring_spec, score_criteria_map, score_junit_criteria

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


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


def _resolve_spec_path(
    run_dir: Path, explicit_spec: Optional[Path], fallback_spec: Optional[Path]
) -> Optional[Path]:
    if explicit_spec is not None:
        return explicit_spec
    local_spec = run_dir / "pack" / "spec.md"
    return local_spec if local_spec.is_file() else fallback_spec


def _collect_run(run_dir: Path, spec_path: Optional[Path], html_dir: Path) -> dict[str, Any]:
    deliverables = run_dir / "deliverables"
    meta_path = run_dir / "run-meta.json"
    report_path = deliverables / "run-report.json"
    junit_path = deliverables / "junit.xml"

    meta: dict[str, Any] = {}
    report: dict[str, Any] = {}
    spec_ids: list[str] = []
    summary: dict[str, Any] = {}
    source = spec_path
    status = "PENDING"
    error = ""
    expected_total = 0
    try:
        if spec_path is not None:
            spec_ids = read_scoring_spec(spec_path)
            expected_total = len(spec_ids)
        if meta_path.exists():
            source = meta_path
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("run metadata must be a JSON object")
            meta = data
            expected_total = expected_total or int(meta.get("criteria_count") or 0)

        criteria: Optional[dict[str, bool]] = None
        unverified: list[str] = []
        if report_path.exists():
            source = report_path
            report, criteria, unverified = read_run_report(report_path)
            if spec_ids:
                flagged = set(unverified)
                unverified = [cid for cid in spec_ids if cid in flagged or cid not in criteria]
                criteria = {cid: criteria[cid] for cid in spec_ids if cid in criteria}
        elif junit_path.exists():
            source = junit_path
            if not spec_ids:
                raise ValueError("JUnit scoring requires spec.md")
            criteria, unverified = score_junit_criteria(junit_path, spec_ids)

        if criteria is not None:
            summary, rc = score_criteria_map(criteria, unverified=unverified, out_stream=io.StringIO())
            if rc != 0:
                raise ValueError("no criteria to score")
            status = "PASS" if summary["passed"] == summary["total"] else "PARTIAL"
    except (OSError, ET.ParseError, TypeError, ValueError, OverflowError) as exc:
        status = "ERROR"
        error = f"{source.name}: {exc}"

    harness = str(report.get("harness") or meta.get("harness") or "?")
    model = str(report.get("model") or meta.get("model") or "?")
    surface = str(report.get("surface") or "").strip()
    taste_mode = str(meta.get("taste_mode") or "?")

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
        "tokens": report.get("tokens", "?"),
        "rounds": report.get("rounds", "?"),
        "status": status,
        "error": error,
        "passed": summary.get("passed", 0),
        "total": summary.get("total", expected_total),
        "pct": summary.get("invariants_percent"),
        "spec_ids": spec_ids,
        "criteria": summary.get("criteria", {}),
        "unverified": set(summary.get("unverified", [])),
        "screenshots": screenshots,
        "summary_md": _read_text(deliverables / "SUMMARY.md"),
        "taste_md": _read_text(deliverables / "TASTE.md"),
        "pack_gaps_md": _read_text(deliverables / "PACK_GAPS.md"),
    }


def _cell_state(run: dict[str, Any], cid: str) -> str:
    if run["spec_ids"] and cid not in run["spec_ids"]:
        return "—"
    if run["status"] in {"PENDING", "ERROR"}:
        return run["status"]
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
        passed_str = f"{r['passed']}/{r['total']}" if r["pct"] is not None else f"—/{r['total'] or '?'}"
        lines.append(
            f"| `{r['dir_name']}` | `{r['harness']}` | `{r['model']}` | **{r['status']}** | "
            f"{r['surface']} | {pct_str} | {passed_str} | {r['tokens']} | {r['rounds']} | {len(r['screenshots'])} |"
        )

    errors = [r for r in runs if r["error"]]
    if errors:
        lines.extend(["", "## Scoring Errors", ""])
        for r in errors:
            lines.append(f"- `{r['dir_name']}` — {' '.join(r['error'].splitlines())}")

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
    completed = sum(1 for r in runs if r["pct"] is not None)
    cards_html: list[str] = []

    for r in runs:
        status_cls = r["status"].lower()
        pct_text = f"{r['pct']:.1f}%" if r["pct"] is not None else "—"
        passed_text = f"{r['passed']}/{r['total']}" if r["pct"] is not None else f"—/{r['total'] or '?'}"
        error_html = f"<p>{html.escape(r['error'])}</p>" if r["error"] else ""

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
  {error_html}
  {gallery}
  <div class="docs">{details}</div>
</article>"""
        )

    matrix_rows: list[str] = []
    for cid in criterion_ids:
        states = [_cell_state(r, cid) for r in runs]
        cells = "".join(f'<td><span class="pill pill-{state.lower()}">{state}</span></td>' for state in states)
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
    .badge-partial, .badge-error, .pill-fail, .pill-error {{ background: var(--fail-bg); color: var(--fail-fg); }}
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

    explicit_spec = spec_path.resolve() if spec_path is not None else None
    fallback_spec = next(
        (p for p in [runs_dir / "spec.md", *(d / "pack" / "spec.md" for d in run_dirs)] if p.is_file()),
        None,
    )

    html_target = (html_out or (runs_dir / "comparison.html")).resolve()
    md_target = (md_out or (runs_dir / "COMPARISON.md")).resolve()
    html_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.parent.mkdir(parents=True, exist_ok=True)

    runs = [
        _collect_run(d, _resolve_spec_path(d, explicit_spec, fallback_spec), html_target.parent)
        for d in run_dirs
    ]
    criterion_ids = sorted(
        {cid for r in runs for cid in (r["spec_ids"] or r["criteria"])}, key=natural_id_key
    )

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
