#!/usr/bin/env python3
"""SpecPack invariants scorer supporting JSON reports and JUnit XML evidence."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    from ._common import criterion_match_pattern, extract_criterion_ids, natural_id_key
except ImportError:
    from _common import criterion_match_pattern, extract_criterion_ids, natural_id_key


def _validate_criteria(criteria: dict[str, bool]) -> None:
    for cid, ok in criteria.items():
        if not isinstance(ok, bool):
            raise ValueError(f"criterion {cid} must have a boolean result")


def read_run_report(path: Path) -> tuple[dict[str, object], dict[str, bool], list[str]]:
    """Read the criterion results and provenance from a JSON report."""
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("criteria"), dict):
        raise ValueError("run report must contain a criteria object")
    _validate_criteria(report["criteria"])

    unverified = report.get("unverified")
    if unverified is None:
        unverified = []
    if not isinstance(unverified, list) or any(not isinstance(cid, str) for cid in unverified):
        raise ValueError("run report unverified must be a list of criterion IDs or null")

    return report, report["criteria"], unverified


def score_criteria_map(
    criteria: dict[str, bool],
    *,
    harness: str = "?",
    model: str = "?",
    surface: str = "",
    tokens: object = "?",
    rounds: object = "?",
    unverified: Optional[list[str]] = None,
    out_stream=None,
) -> tuple[dict[str, object], int]:
    """Compute per-area and total invariant satisfaction and print a formatted summary."""
    stream = out_stream or sys.stdout
    _validate_criteria(criteria)

    unverified = sorted(set(unverified or []), key=natural_id_key)
    criteria = {**criteria, **dict.fromkeys(unverified, False)}
    if not criteria:
        print("no criteria to score", file=stream)
        return {}, 1

    areas: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for cid, ok in criteria.items():
        area = str(cid).split(".")[0]
        areas[area][1] += 1
        areas[area][0] += int(ok)

    total_ok = sum(v[0] for v in areas.values())
    total = sum(v[1] for v in areas.values())
    pct = 100.0 * total_ok / total if total else 0.0

    print(f"Harness: {harness}  Model: {model}", file=stream)
    if surface:
        print(f"Surface: {surface}", file=stream)
    print(f"Tokens: {tokens}  Rounds: {rounds}", file=stream)
    for area in sorted(areas, key=natural_id_key):
        ok, count = areas[area]
        print(f"  Requirement {area}: {ok}/{count} = {100.0 * ok / count:.0f}%", file=stream)
    print(f"INVARIANTS: {total_ok}/{total} = {pct:.1f}%", file=stream)

    failed = sorted((c for c, ok in criteria.items() if not ok), key=natural_id_key)
    if failed:
        print("Failed criteria:", ", ".join(failed), file=stream)
    if unverified:
        print("Unverified criteria (no executed test):", ", ".join(unverified), file=stream)

    summary = {
        "harness": harness,
        "model": model,
        "surface": surface,
        "tokens": tokens,
        "rounds": rounds,
        "invariants_percent": round(pct, 1),
        "passed": total_ok,
        "total": total,
        "criteria": {k: criteria[k] for k in sorted(criteria, key=natural_id_key)},
        "failed": failed,
        "unverified": unverified,
    }
    return summary, 0


def read_scoring_spec(spec_path: Path) -> list[str]:
    """Read a nonempty, unambiguous set of criterion IDs for scoring."""
    spec_ids, duplicates = extract_criterion_ids(spec_path)
    if duplicates:
        raise ValueError(f"Duplicate criterion IDs in {spec_path}: {', '.join(duplicates)}")
    if not spec_ids:
        raise ValueError(f"No bracketed criterion IDs (e.g. [1.1]) found in {spec_path}")
    return spec_ids


def score_junit_report(junit_path: Path, spec_path: Path) -> tuple[dict[str, bool], list[str]]:
    """Map executed JUnit XML <testcase> results onto spec.md criterion IDs."""
    return score_junit_criteria(junit_path, read_scoring_spec(spec_path))


def score_junit_criteria(junit_path: Path, spec_ids: list[str]) -> tuple[dict[str, bool], list[str]]:
    """Score JUnit evidence against previously resolved criterion IDs."""
    tree = ET.parse(junit_path)
    root = tree.getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError(f"Expected a JUnit testsuite or testsuites root in {junit_path}")

    patterns = {cid: criterion_match_pattern(cid) for cid in spec_ids}
    counts: dict[str, dict[str, int]] = {
        cid: {"passed": 0, "failed": 0, "skipped": 0} for cid in spec_ids
    }

    for tc in root.iter("testcase"):
        name = tc.attrib.get("name", "")
        classname = tc.attrib.get("classname", "")
        target = f"{classname} {name}"
        has_fail = tc.find("failure") is not None or tc.find("error") is not None
        has_skip = tc.find("skipped") is not None

        for cid, pattern in patterns.items():
            if not pattern.search(target):
                continue
            if has_fail:
                counts[cid]["failed"] += 1
            elif has_skip:
                counts[cid]["skipped"] += 1
            else:
                counts[cid]["passed"] += 1

    criteria: dict[str, bool] = {}
    unverified: list[str] = []
    for cid in spec_ids:
        c = counts[cid]
        total_matched = c["passed"] + c["failed"] + c["skipped"]
        if total_matched == 0:
            unverified.append(cid)
            criteria[cid] = False
        else:
            criteria[cid] = c["passed"] >= 1 and c["failed"] == 0 and c["skipped"] == 0

    return criteria, unverified


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score SpecPack core invariant satisfaction from run-report.json or JUnit XML + spec.md."
    )
    parser.add_argument(
        "report",
        nargs="?",
        default=None,
        help="Path to run-report.json (default when --junit is not set: run-report.json).",
    )
    parser.add_argument("--junit", type=Path, help="Path to JUnit XML test results file.")
    parser.add_argument("--spec", type=Path, help="Path to pack spec.md defining [X.Y] invariants.")
    parser.add_argument("--harness", help="Rebuilding agent harness name.")
    parser.add_argument("--model", help="Model identifier used for rebuild.")
    parser.add_argument("--surface", help="Chosen UI surface / style (e.g. Web UI, macOS menu bar).")
    parser.add_argument("--tokens", help="Total tokens consumed.")
    parser.add_argument("--rounds", help="Conversations / rounds used.")
    parser.add_argument("--json-out", type=Path, help="Optional path to write scored run report JSON.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if (args.junit is None) != (args.spec is None):
        parser.error("--junit and --spec must be provided together.")
    if args.junit is not None and args.report is not None:
        parser.error("a JSON report path cannot be used with --junit.")

    source = args.junit or Path(args.report or "run-report.json")
    report: dict[str, object] = {}
    try:
        if args.junit is not None:
            criteria, unverified = score_junit_report(args.junit, args.spec)
        else:
            report, criteria, unverified = read_run_report(source)

        metadata = {}
        for key, default in (("harness", "?"), ("model", "?"), ("surface", ""), ("tokens", "?"), ("rounds", "?")):
            override = getattr(args, key)
            metadata[key] = override if override is not None else report.get(key, default)
        for key in ("harness", "model", "surface"):
            metadata[key] = str(metadata[key])
        summary, rc = score_criteria_map(
            criteria,
            unverified=unverified,
            **metadata,
        )
    except (OSError, ET.ParseError, ValueError) as exc:
        print(f"error: failed to score {source}: {exc}", file=sys.stderr)
        return 1

    if rc == 0 and args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
            fh.write("\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
