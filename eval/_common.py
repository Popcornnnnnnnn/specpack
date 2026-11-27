"""Shared helpers for SpecPack validation and parity scoring."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

CRITERION_LINE_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\[([1-9]\d*(?:\.\d+)+)\]")


def natural_id_key(identifier: str) -> Tuple[int, Tuple[Tuple[int, object], ...]]:
    """Sort key so '2' < '10' and '1.2' < '1.10', keeping non-numeric strings last."""
    parts = []
    has_non_digit = False
    for token in str(identifier).split("."):
        if token.isdigit():
            parts.append((0, int(token)))
        else:
            has_non_digit = True
            parts.append((1, token))
    return (1 if has_non_digit else 0, tuple(parts))


def strip_fenced_code_blocks(text: str) -> list[tuple[int, str]]:
    """Return 1-based (line_number, line_text) pairs outside triple-backtick fences."""
    result: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            result.append((lineno, line))
    return result


def extract_criterion_ids(spec_path: Path) -> tuple[list[str], list[str]]:
    """Extract ordered unique bracketed criterion IDs and any duplicates from spec.md."""
    text = spec_path.read_text(encoding="utf-8")
    ordered: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for _, line in strip_fenced_code_blocks(text):
        match = CRITERION_LINE_RE.match(line)
        if not match:
            continue
        cid = match.group(1)
        if cid in seen:
            duplicates.append(cid)
        else:
            seen.add(cid)
            ordered.append(cid)
    return ordered, duplicates


def criterion_match_pattern(cid: str) -> re.Pattern[str]:
    """Compile boundary-safe regex matching '[1.1]', '1.1', or '1_1' in test identifiers."""
    esc_dot = re.escape(cid)
    esc_under = re.escape(cid.replace(".", "_"))
    # Keep HTTP version strings from counting as evidence for a criterion.
    pre = r"(?<![0-9])(?<![0-9]\.)(?<![0-9]_)(?<!(?i:http)[/_])"
    post = r"(?![0-9])(?!\.[0-9])(?!_[0-9])"
    return re.compile(rf"(?:\[{esc_dot}\]|{pre}(?:{esc_dot}|{esc_under}){post})")
