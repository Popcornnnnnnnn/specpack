#!/usr/bin/env python3
"""Minimal SpecPack parity scorer.

Reads a run report JSON:
  {"criteria": {"1.1": true, "1.2": false, ...},
   "harness": "...", "model": "...", "tokens": 0, "rounds": 0}
Prints total and per-requirement-area parity.
Usage: python3 eval/score.py run-report.json
"""
import json, sys
from collections import defaultdict

def main(path):
    r = json.load(open(path))
    crit = r.get("criteria", {})
    if not crit:
        print("no criteria in report"); return 1
    areas = defaultdict(lambda: [0, 0])
    for cid, ok in crit.items():
        area = str(cid).split(".")[0]
        areas[area][1] += 1
        areas[area][0] += bool(ok)
    total_ok = sum(v[0] for v in areas.values()); total = sum(v[1] for v in areas.values())
    print(f"Harness: {r.get('harness','?')}  Model: {r.get('model','?')}")
    print(f"Tokens: {r.get('tokens','?')}  Rounds: {r.get('rounds','?')}")
    for a in sorted(areas):
        ok, n = areas[a]; print(f"  Requirement {a}: {ok}/{n} = {100*ok/n:.0f}%")
    print(f"PARITY: {total_ok}/{total} = {100*total_ok/total:.1f}%")
    failed = [c for c, ok in crit.items() if not ok]
    if failed: print("Failed criteria:", ", ".join(sorted(failed)))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "run-report.json"))
