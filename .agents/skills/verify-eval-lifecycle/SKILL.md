---
name: verify-eval-lifecycle
description: Check the SpecPack trial preparation, scoring, and comparison lifecycle with TLA+ and TLC after changes to eval logic or a major update.
---

# Verify the SpecPack eval lifecycle

`sync_commit`: `d795d3f8032faccbfa8a0d5b42c7ae07ece11491`

## Coverage

| Invariant | Rule and code |
| --- | --- |
| `OnlyCompleteTrialIsVisible` | Comparison can discover a trial only after its scaffold is complete. Preparation failures leave no published trial from that attempt. See `prepare_trial`, `_init_git_repo`, and `_write_zip_bundle` in `eval/prepare_run.py`, `validate_pack` in `eval/validate.py`, and `_discover_run_dirs` in `eval/compare.py`. |
| `PassRequiresCompleteEvidence` | A pass requires a verified true result for every criterion in the selected spec. Missing results are unverified. Extra IDs and summary claims contribute nothing to the score. See `_resolve_spec_path`, `_collect_run`, and `compare_runs` in `eval/compare.py`, `score_junit_criteria` in `eval/score.py`, and `criterion_match_pattern` in `eval/_common.py`. |
| `RescorePreservesUnverified` | An unverified JSON criterion stays unverified and earns no credit on rescore. See `read_run_report`, `score_criteria_map`, and `main` in `eval/score.py`. |
| `ComparisonDistinguishesPendingAndError` | Missing evidence produces `PENDING`. Corrupt or unscorable evidence produces `ERROR`. See `_collect_run` in `eval/compare.py` and `read_run_report`, `read_scoring_spec`, and `score_junit_criteria` in `eval/score.py`. |

The finite model follows one preparation attempt and one comparison, with an optional zip and one optional JSON rescore. It uses two small overlapping specs and representative JSON and JUnit inputs. Pack validation, individual parsing rules, and filesystem errors enter as outcomes. The model assumes an atomic same-filesystem rename and a successful rollback after an ordinary zip publication error. Python tests exercise the real parser and filesystem behavior. Process interruption, interference from other writers, and arbitrary file contents are outside the model.

## Run and interpret

1. From the repo root, diff `eval/` against `sync_commit`, including local edits. If covered behavior changed, use `/maintain-formal-verification-skill` to recheck the mapping from Python to TLA+.
2. Run `/statechart` with `formal/SpecPackEvalLifecycle.tla`, `formal/SpecPackEvalLifecycle.cfg`, and `formal/specpack-view.mjs`. Use a fresh output folder under `/tmp`. Pass requires exit `0`, all four invariants, and `NoDeadlock`. TLC 2.19 checked 33 states at `sync_commit`.
3. Replay any shortest violation against the Python entry point in a temporary fixture. If it reproduces, fix the code and add a regression. If the trace cannot occur, correct the model. Advance `sync_commit` only after confirming alignment and rerunning the checks.

To check that the rules can fail, use a scratch copy of the model. Publish the scaffold during `StartStaging`, let a JSON summary claim grant `PASS`, discard flags in `RescoreReport`, and label corrupt evidence `PENDING`. TLC reported all four violations with those mutations. The matching tests in `tests/test_eval.py` pass against the fixed code.
