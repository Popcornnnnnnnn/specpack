import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from eval import _common, score, validate

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_clean_pack(pack_dir: Path) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("examples", "reference", "tests"):
        (pack_dir / sub).mkdir(exist_ok=True)

    (pack_dir / "pack.yaml").write_text(
        "\n".join(
            [
                "name: demo-pack",
                'format_version: "0.2"',
                "version: 0.1.0",
                "description: Small deterministic demo pack for validator tests.",
                "regenerability:",
                "  budget_days: 2",
                "  budget_conversations: 30",
                "  budget_tokens: 20000000",
                "  measured: []",
                "license: MIT",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                "name: demo-pack",
                "description: Build your own version of Demo Pack following spec.md.",
                "---",
                "",
                "# Build Instructions (Freedom by Default)",
                "",
                "Read `spec.md` invariants strictly, then `decisions.md` as advisory field notes.",
                "Run a short Personalisation Interview (chosen surface, style) before coding.",
                "Budgets allow < 50M tokens and links like <https://example.com>.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Demo Pack — Core Invariants",
                "",
                "## Problem & Intent",
                "Deterministic parser specification.",
                "",
                "## Non-goals",
                "- No live network fetches.",
                "",
                "## Core Invariants",
                "",
                "### Requirement 1: Parsing",
                "- [1.1] WHEN valid input arrives THEN the system SHALL emit normalized JSON.",
                "- [1.2] WHEN invalid input arrives THEN the system SHALL exit non-zero.",
                "",
                "```markdown",
                "- [99.1] Example inside a code fence must be ignored.",
                "```",
                "",
                "### Requirement 2: Output",
                "- [2.1] WHEN `--format csv` is passed THEN the system SHALL output CSV rows.",
                "",
                "### Requirement 10: Diagnostics",
                "- [10.1] WHEN `--verbose` is passed THEN the system SHALL log timing.",
                "- [1.10] WHEN input is empty THEN the system SHALL emit an empty array.",
                "",
                "## Measurable success",
                "- 100% invariant coverage on scenario tests.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "decisions.md").write_text(
        "\n".join(
            [
                "# Field Notes & Advice",
                "",
                "## Reference choices (advisory)",
                "### Choice 1: Stdlib-only parser",
                "- **What the reference build picked:** Pure Python stdlib.",
                "- **Why:** Zero dependency setup.",
                "- **Clean alternatives:** Any typed parser.",
                "",
                "## Dead ends & traps",
                "- Avoid regex-only line splitting on nested records.",
                "",
                "## Taste calls",
                "- Fail loudly on malformed JSON.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "eval.md").write_text(
        "# Eval\n\nRun `pytest --junitxml=results.xml` and score with `eval/score.py`.\n",
        encoding="utf-8",
    )


class TestScore(unittest.TestCase):
    def test_json_report_numeric_sorting_and_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "run-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "harness": "codex",
                        "model": "test-model",
                        "surface": "TUI (Ratatui)",
                        "tokens": 12000,
                        "rounds": 4,
                        "criteria": {
                            "10.1": True,
                            "2.1": False,
                            "1.10": False,
                            "1.2": True,
                            "1.1": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "eval" / "score.py"), str(report_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            lines = proc.stdout.splitlines()
            req_lines = [line.strip() for line in lines if line.strip().startswith("Requirement ")]
            self.assertEqual(
                [line.split(":")[0] for line in req_lines],
                ["Requirement 1", "Requirement 2", "Requirement 10"],
            )
            self.assertIn("Surface: TUI (Ratatui)", proc.stdout)
            self.assertIn("INVARIANTS: 2/5 = 40.0%", proc.stdout)
            self.assertIn("Failed criteria: 1.1, 1.10, 2.1", proc.stdout)

    def test_junit_scoring_boundary_and_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_dir = root / "pack"
            _write_clean_pack(pack_dir)
            junit_path = root / "results.xml"
            out_json = root / "out" / "scored.json"

            # Criteria in spec.md: 1.1, 1.2, 2.1, 10.1, 1.10 (code-fenced 99.1 ignored!)
            junit_xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="suite" tests="6">
    <!-- Matches ONLY 1.10, must NOT satisfy 1.1 -->
    <testcase classname="tests.contract" name="test_1_10_empty_input" time="0.01"/>
    <!-- Matches ONLY 1.2 (passed across two testcases) -->
    <testcase classname="tests.contract" name="test_[1.2]_invalid_a" time="0.01"/>
    <testcase classname="tests.contract" name="test_1.2_invalid_b" time="0.01"/>
    <!-- Matches 2.1 (one pass, one skipped -> criterion must FAIL) -->
    <testcase classname="tests.contract" name="test_2_1_csv_a" time="0.01"/>
    <testcase classname="tests.contract" name="test_2_1_csv_b" time="0.01">
      <skipped message="todo"/>
    </testcase>
    <!-- Matches 10.1 (explicit failure) -->
    <testcase classname="tests.contract" name="test_10_1_verbose" time="0.01">
      <failure message="assertion failed">diff</failure>
    </testcase>
    <!-- 2_1_1 must NOT falsely satisfy 1.1 -->
    <testcase classname="tests.contract" name="test_2_1_1_unrelated" time="0.01"/>
  </testsuite>
</testsuites>
"""
            junit_path.write_text(junit_xml, encoding="utf-8")

            criteria, unverified = score.score_junit_report(junit_path, pack_dir / "spec.md")
            self.assertNotIn("99.1", criteria)
            self.assertEqual(unverified, ["1.1"])
            self.assertFalse(criteria["1.1"])
            self.assertTrue(criteria["1.2"])
            self.assertTrue(criteria["1.10"])
            self.assertFalse(criteria["2.1"])
            self.assertFalse(criteria["10.1"])

            rc = score.main(
                [
                    "--junit",
                    str(junit_path),
                    "--spec",
                    str(pack_dir / "spec.md"),
                    "--harness",
                    "codex",
                    "--model",
                    "gpt",
                    "--surface",
                    "Web Dashboard (React)",
                    "--tokens",
                    "50000",
                    "--rounds",
                    "3",
                    "--json-out",
                    str(out_json),
                ]
            )
            self.assertEqual(rc, 0)
            scored = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(scored["surface"], "Web Dashboard (React)")
            self.assertEqual(scored["invariants_percent"], 40.0)
            self.assertEqual(scored["passed"], 2)
            self.assertEqual(scored["total"], 5)
            self.assertEqual(scored["unverified"], ["1.1"])
            self.assertEqual(scored["failed"], ["1.1", "2.1", "10.1"])

    def test_junit_requires_spec_flag(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "eval" / "score.py"), "--junit", "x.xml"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)


class TestValidate(unittest.TestCase):
    def test_clean_pack_passes_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            errors, warnings, count = validate.validate_pack(pack)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertEqual(count, 5)
            self.assertEqual(validate.main([str(pack), "--strict"]), 0)

    def test_legacy_golden_dir_warns_not_fails_non_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            shutil.rmtree(pack / "reference")
            (pack / "golden").mkdir()
            errors, warnings, _ = validate.validate_pack(pack)
            self.assertEqual(errors, [])
            self.assertTrue(any("legacy 'golden/'" in w for w in warnings))
            self.assertEqual(validate.main([str(pack)]), 0)
            self.assertEqual(validate.main([str(pack), "--strict"]), 1)

    def test_missing_personalisation_prompt_warns_and_fails_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            (pack / "SKILL.md").write_text(
                "---\nname: demo-pack\ndescription: Short guide.\n---\n\nFollow spec.md.\n",
                encoding="utf-8",
            )
            errors, warnings, _ = validate.validate_pack(pack)
            self.assertEqual(errors, [])
            self.assertTrue(any("personalisation interview" in w for w in warnings))
            self.assertEqual(validate.main([str(pack)]), 0)
            self.assertEqual(validate.main([str(pack), "--strict"]), 1)

    def test_missing_required_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            (pack / "decisions.md").unlink()
            errors, _, _ = validate.validate_pack(pack)
            self.assertTrue(any("decisions.md" in e for e in errors))
            self.assertEqual(validate.main([str(pack)]), 1)

    def test_skill_frontmatter_name_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            (pack / "SKILL.md").write_text(
                "---\nname: wrong-name\ndescription: Mismatch.\n---\n\nPersonalisation options.\n",
                encoding="utf-8",
            )
            errors, _, _ = validate.validate_pack(pack)
            self.assertTrue(any("does not match pack.yaml" in e for e in errors))
            self.assertEqual(validate.main([str(pack)]), 1)

    def test_duplicate_criterion_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            spec = pack / "spec.md"
            spec.write_text(
                spec.read_text(encoding="utf-8") + "\n- [1.1] Duplicate criterion.\n",
                encoding="utf-8",
            )
            errors, _, _ = validate.validate_pack(pack)
            self.assertTrue(any("Duplicate criterion IDs" in e for e in errors))
            self.assertEqual(validate.main([str(pack)]), 1)

    def test_placeholder_warns_non_strict_and_fails_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            _write_clean_pack(pack)
            eval_md = pack / "eval.md"
            eval_md.write_text("# Eval\n\nRun `<exact command>` here.\n", encoding="utf-8")
            errors, warnings, _ = validate.validate_pack(pack)
            self.assertEqual(errors, [])
            self.assertTrue(any("<exact command>" in w for w in warnings))
            self.assertEqual(validate.main([str(pack)]), 0)
            self.assertEqual(validate.main([str(pack), "--strict"]), 1)

    def test_repo_templates_and_signal_validate_without_errors(self) -> None:
        for rel in ("templates/pack", "examples/signal"):
            self.assertEqual(validate.main([str(REPO_ROOT / rel)]), 0, rel)

    def test_port_tools_pack_validates_strict_and_harness_runs(self) -> None:
        pack = REPO_ROOT / "examples/port-tools"
        self.assertEqual(validate.main([str(pack), "--strict"]), 0)

        spec_ids, duplicates = _common.extract_criterion_ids(pack / "spec.md")
        self.assertEqual(duplicates, [])
        self.assertEqual(len(spec_ids), 12)

        scenarios_data = json.loads((pack / "examples/scenarios.json").read_text(encoding="utf-8"))
        covered = set()
        for scenario in scenarios_data["scenarios"]:
            covered.update(scenario["criteria"])
        self.assertEqual(covered, set(spec_ids))

        harness = pack / "tests/contract_harness.py"
        compile(harness.read_text(encoding="utf-8"), str(harness), "exec")
        proc = subprocess.run(
            [sys.executable, str(harness), "--self-test"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
