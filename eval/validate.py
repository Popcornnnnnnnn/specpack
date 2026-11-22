#!/usr/bin/env python3
"""Validate a SpecPack directory for structure, manifest, frontmatter, and criteria."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

try:
    from ._common import extract_criterion_ids, strip_fenced_code_blocks
except ImportError:
    from _common import extract_criterion_ids, strip_fenced_code_blocks

REQUIRED_FILES = ("pack.yaml", "SKILL.md", "spec.md", "decisions.md")
RECOMMENDED_PATHS = ("eval.md", "tests", "examples", "golden")
PLACEHOLDER_SCAN_FILES = ("SKILL.md", "spec.md", "decisions.md", "eval.md")
PLACEHOLDER_RE = re.compile(r"(?<!<)<([A-Za-z][A-Za-z0-9 .,/:'\"()_-]{0,79})>(?!>)")


def _strip_yaml_scalar(raw: str) -> str:
    """Strip inline comment (outside quotes) and surrounding quotes from a YAML scalar."""
    text = raw.strip()
    if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
        return text[1:-1].strip()
    if "#" in text:
        text = text.split("#", 1)[0].strip()
    if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
        return text[1:-1].strip()
    return text


def _parse_pack_yaml(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Minimal stdlib parser for top-level keys and regenerability scalars in pack.yaml."""
    top: dict[str, str] = {}
    regen: dict[str, str] = {}
    in_regen = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0:
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            in_regen = key == "regenerability"
            top[key] = _strip_yaml_scalar(val)
        elif in_regen and indent > 0 and not line.startswith("-") and ":" in line:
            key, val = line.split(":", 1)
            regen[key.strip()] = _strip_yaml_scalar(val)

    return top, regen


def _parse_frontmatter(path: Path) -> tuple[Optional[dict[str, str]], list[str]]:
    """Parse leading YAML frontmatter in SKILL.md."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None, ["SKILL.md is missing leading YAML frontmatter (`---`)."]

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, ["SKILL.md YAML frontmatter is missing a closing `---` delimiter."]

    meta: dict[str, str] = {}
    for line in lines[1:end_idx]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = _strip_yaml_scalar(v)
    return meta, []


def _find_headings(path: Path) -> set[str]:
    """Return normalized lowercase level-2 headings outside fenced code blocks."""
    headings: set[str] = set()
    for _, line in strip_fenced_code_blocks(path.read_text(encoding="utf-8")):
        match = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if match:
            headings.add(match.group(1).strip().lower())
    return headings


def _find_placeholders(path: Path) -> list[tuple[int, str]]:
    """Find unfilled <placeholder> markers outside fenced code blocks."""
    hits: list[tuple[int, str]] = []
    for lineno, line in strip_fenced_code_blocks(path.read_text(encoding="utf-8")):
        for match in PLACEHOLDER_RE.finditer(line):
            inner = match.group(1)
            if inner.lower().startswith(("http://", "https://", "mailto:")):
                continue
            hits.append((lineno, f"<{inner}>"))
    return hits


def validate_pack(pack_dir: Path) -> tuple[list[str], list[str], int]:
    """Validate a SpecPack directory, returning (errors, warnings, criterion_count)."""
    errors: list[str] = []
    warnings: list[str] = []
    criterion_count = 0

    if not pack_dir.is_dir():
        return [f"Pack directory does not exist: {pack_dir}"], warnings, 0

    for rel in REQUIRED_FILES:
        if not (pack_dir / rel).is_file():
            errors.append(f"Missing required file: {rel}")

    for rel in RECOMMENDED_PATHS:
        if not (pack_dir / rel).exists():
            warnings.append(f"Missing recommended path: {rel}")

    pack_yaml_path = pack_dir / "pack.yaml"
    pack_name = ""
    if pack_yaml_path.is_file():
        top, regen = _parse_pack_yaml(pack_yaml_path)
        pack_name = top.get("name", "")
        for key in ("name", "version", "license"):
            if not top.get(key):
                errors.append(f"pack.yaml is missing non-empty '{key}'.")
        if not top.get("description"):
            warnings.append("pack.yaml has an empty 'description'.")
        for bkey in ("budget_days", "budget_conversations", "budget_tokens"):
            raw_val = regen.get(bkey, "")
            try:
                num = float(raw_val)
                if num <= 0:
                    raise ValueError
            except ValueError:
                errors.append(f"pack.yaml regenerability.{bkey} must be a positive number.")

    skill_path = pack_dir / "SKILL.md"
    if skill_path.is_file():
        meta, fm_errors = _parse_frontmatter(skill_path)
        errors.extend(fm_errors)
        if meta is not None:
            skill_name = meta.get("name", "")
            if not skill_name:
                errors.append("SKILL.md frontmatter is missing 'name'.")
            elif pack_name and skill_name != pack_name:
                errors.append(
                    f"SKILL.md frontmatter name '{skill_name}' does not match pack.yaml name '{pack_name}'."
                )
            if not meta.get("description"):
                warnings.append("SKILL.md frontmatter is missing 'description'.")

    spec_path = pack_dir / "spec.md"
    if spec_path.is_file():
        criteria, duplicates = extract_criterion_ids(spec_path)
        criterion_count = len(criteria)
        if duplicates:
            errors.append(f"Duplicate criterion IDs in spec.md: {', '.join(duplicates)}")
        if criterion_count == 0:
            warnings.append("No bracketed criterion IDs (e.g. '- [1.1] WHEN ...') found in spec.md.")
        headings = _find_headings(spec_path)
        if not any(h.startswith("non-goals") for h in headings):
            errors.append("spec.md must include a '## Non-goals' section.")

    decisions_path = pack_dir / "decisions.md"
    if decisions_path.is_file():
        d_headings = _find_headings(decisions_path)
        if not any(h.startswith("dead ends") for h in d_headings):
            errors.append("decisions.md must include a '## Dead ends' section.")
        if not any(h.startswith("taste calls") for h in d_headings):
            errors.append("decisions.md must include a '## Taste calls' section.")

    for rel in PLACEHOLDER_SCAN_FILES:
        fpath = pack_dir / rel
        if fpath.is_file():
            for lineno, tag in _find_placeholders(fpath):
                warnings.append(f"{rel}:{lineno}: unfilled placeholder {tag}")

    return errors, warnings, criterion_count


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a SpecPack directory.")
    parser.add_argument("pack_dir", type=Path, help="Path to the pack directory to validate.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (including missing recommended paths or unfilled <placeholders>).",
    )
    args = parser.parse_args(argv)

    errors, warnings, criterion_count = validate_pack(args.pack_dir)
    for err in errors:
        print(f"ERROR: {err}")
    for warn in warnings:
        print(f"WARN:  {warn}")

    ok = len(errors) == 0 and (not args.strict or len(warnings) == 0)
    status = "PASS" if ok else "FAIL"
    print(f"{status}: {args.pack_dir} ({criterion_count} criteria, {len(errors)} errors, {len(warnings)} warnings)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
