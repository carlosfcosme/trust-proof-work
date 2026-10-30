"""The gate + benchmark runner.

Part A - THE GATE (Day-3): the frozen rig, run cold against the 10-skill
corpus, must reproduce exactly 8 Safe / 2 Caution / 0 Do-Not-Install and
match the locked ground truth skill-for-skill. Exit code is non-zero if
the gate fails; nothing downstream may proceed on a failed gate.

Part B - gauntlet v1 baseline: frozen rig only, against the locked
expected verdicts (the 2026-10-21 run recorded 13/20 exact, 3/6 burns).

Part C - gauntlet v1 with the Day-4 rule fixes (tpw.proof.final_verdict).

Part D - gauntlet v2 deck with the fixes (informational; verdicts locked
2026-10-21 before any run).

Writes out/gate-report.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "rig"))

import evidence              # noqa: E402
import verdicts as rig_verdicts  # noqa: E402

from tpw import proof, rulefixes  # noqa: E402


def run_deck(fixtures_dir: Path, expected_path: Path, with_fixes: bool):
    expected = {f["id"]: f["expected_verdict"]
                for f in json.loads(expected_path.read_text())["fixtures"]}
    per = {}
    for fid, exp in expected.items():
        d = fixtures_dir / fid
        scan = evidence.scan_skill(d, fid)
        base = rig_verdicts.verdict_for(d, scan)
        if with_fixes:
            fixes = rulefixes.apply_fixes(d, scan)
            actual = proof.final_verdict(base, fixes)
        else:
            actual = base["verdict"]
        per[fid] = {"expected": exp, "actual": actual,
                    "match": actual == exp}
    exact = sum(1 for v in per.values() if v["match"])
    burns = [k for k, v in per.items() if v["expected"] == "Do-Not-Install"]
    burns_caught = sum(1 for k in burns if per[k]["actual"] == "Do-Not-Install")
    clean_fp = sum(1 for v in per.values()
                   if v["expected"] == "Safe" and v["actual"] != "Safe")
    return {"exact": exact, "total": len(per), "burns_caught": burns_caught,
            "burns_total": len(burns), "clean_fp": clean_fp, "per_fixture": per}


def main() -> int:
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    report = {}

    # Part A - corpus gate
    manifest = json.loads((ROOT / "corpus" / "corpus-manifest.json").read_text())
    truth = {c["skill"]: c["ground_truth_verdict"] for c in manifest["corpus"]}
    got = {}
    for skill in truth:
        d = ROOT / "corpus" / "skills" / skill
        got[skill] = rig_verdicts.verdict_for(
            d, evidence.scan_skill(d, skill))["verdict"]
    tally = {"Safe": 0, "Caution": 0, "Do-Not-Install": 0}
    for v in got.values():
        tally[v] += 1
    gate_pass = tally == {"Safe": 8, "Caution": 2, "Do-Not-Install": 0} \
        and got == truth
    report["corpus"] = {"tally": tally, "matches_truth": got == truth,
                        "gate_pass": gate_pass, "per_skill": got}
    print(f"GATE corpus: tally={tally} matches_truth={got == truth} "
          f"-> {'PASS' if gate_pass else 'FAIL'}")

    # Parts B/C/D - gauntlet
    gdir = ROOT / "gauntlet"
    base = run_deck(gdir / "fixtures", gdir / "expected.json", False)
    after = run_deck(gdir / "fixtures", gdir / "expected.json", True)
    v2 = run_deck(gdir / "fixtures-v2", gdir / "expected-v2.json", True)
    report["gauntlet"] = {
        "baseline_exact": base["exact"], "baseline_burns": base["burns_caught"],
        "after_exact": after["exact"], "after_burns": after["burns_caught"],
        "after_clean_fp": after["clean_fp"], "per_fixture": after["per_fixture"]}
    report["gauntlet_v2_after"] = {"exact": v2["exact"], "total": v2["total"],
                                   "per_fixture": v2["per_fixture"]}
    print(f"Gauntlet v1 baseline: {base['exact']}/20 exact, "
          f"burns {base['burns_caught']}/6")
    print(f"Gauntlet v1 + fixes:  {after['exact']}/20 exact, "
          f"burns {after['burns_caught']}/6, clean FP {after['clean_fp']}/8")
    print(f"Gauntlet v2 + fixes:  {v2['exact']}/{v2['total']} exact")
    for fid, v in after["per_fixture"].items():
        if not v["match"]:
            print(f"  v1 miss: {fid} expected {v['expected']} got {v['actual']}")
    for fid, v in v2["per_fixture"].items():
        if not v["match"]:
            print(f"  v2 miss: {fid} expected {v['expected']} got {v['actual']}")

    (out / "gate-report.json").write_text(json.dumps(report, indent=1))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
