#!/usr/bin/env python3
"""GAUNTLET RUNNER — measure the frozen audit/verdict machinery against
pre-registered methodology verdicts on 20 synthetic fixture skills.

Machinery under test (READ-ONLY — imported, never modified):
  rig/evidence.py (vendored at the repository root)
      scan_skill() -> runs the frozen scanner audit_skill.py (sha256-locked
      copy of the 2026-10-07 audit harness) over a skill directory.
  rig/verdicts.py (vendored at the repository root)
      verdict_for() -> the deterministic verdict mapper (rules DNI-B64,
      DNI-RTD, DNI-EVAL, R-CDN, R-BASH).

Expected verdicts live in expected.json, registered 2026-10-21 BEFORE the
first run. This runner only reads them; a divergence between expected and
actual is a finding about the machinery, recorded in results.json and
RESULTS.md — fixtures and expectations are never tuned to the output.

Scope note: this exercises the scanner + verdict mapper only. The
Interrogator citation checker is a labeled test double in the crew rig,
not part of the frozen audit machinery, and is out of scope here (the
crew test covers it: crews-test/meta/RESULTS.md).

Exit code: 0 = the measurement completed (misses are data, not runner
failure). Nonzero = the machinery itself failed to run on some fixture.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_LOCAL_RIG = HERE / "rig"
_REPO_RIG = HERE.parent / "rig"
DOUBLES = _LOCAL_RIG if (_LOCAL_RIG / "evidence.py").exists() else _REPO_RIG
sys.path.insert(0, str(DOUBLES))

from evidence import scan_skill   # noqa: E402  (frozen rig, read-only)
from verdicts import verdict_for  # noqa: E402  (frozen rig, read-only)

SEVERITY = {"Safe": 0, "Caution": 1, "Do-Not-Install": 2}


def evidence_summary(scan):
    """Which scanner checks surfaced evidence (counts + hosts)."""
    c2, c3, c4, c5 = (scan["check2_network"], scan["check3_code"],
                      scan["check4_data"], scan["check5_update"])
    return {
        "urls_hosts": [h for h, _ in c2["urls"]],
        "netcall_files": c2["netcall_files"],
        "scripts": c3["scripts"],
        "eval_hits": c3["eval_hits"],
        "b64_hits": c3["b64_hits"],
        "runtime_download_hits": c3["runtime_download_hits"],
        "sensitive_hits_count": len(c4["sensitive_hits"]),
        "home_refs_count": len(c4["home_refs"]),
        "update_hits": c5["update_hits"],
        "tools_mentions": scan["check1_permissions"].get("tools_mentions", []),
        "hooks_mentions": scan["check1_permissions"].get("hooks_mentions", []),
    }


def main():
    expected = {f["id"]: f for f in
                json.loads((HERE / "expected.json").read_text())["fixtures"]}
    results, failures = [], []
    for fid in sorted(expected):
        skill_dir = HERE / "fixtures" / fid
        try:
            scan = scan_skill(skill_dir, fid)
            draft = verdict_for(skill_dir, scan)
        except Exception as e:  # machinery failed to run — record, don't hide
            failures.append({"fixture": fid, "error": repr(e)})
            continue
        exp = expected[fid]["expected_verdict"]
        act = draft["verdict"]
        if SEVERITY[act] < SEVERITY[exp]:
            outcome = "MISS (under-detected)"
        elif SEVERITY[act] > SEVERITY[exp]:
            outcome = "OVER-FIRE (over-detected)"
        else:
            outcome = "MATCH"
        results.append({
            "fixture": fid,
            "category": expected[fid]["category"],
            "planted_property": expected[fid]["planted_property"],
            "expected_verdict": exp,
            "actual_verdict": act,
            "rules_fired": draft["rules_fired"],
            "outcome": outcome,
            "evidence": evidence_summary(scan),
        })

    burns = [r for r in results if r["expected_verdict"] == "Do-Not-Install"]
    cleans = [r for r in results if r["expected_verdict"] == "Safe"]
    cautions = [r for r in results if r["expected_verdict"] == "Caution"]
    summary = {
        "fixtures_run": len(results),
        "machinery_failures": failures,
        "exact_matches": sum(r["outcome"] == "MATCH" for r in results),
        "burn_fixtures": len(burns),
        "burns_detected_as_dni": sum(r["actual_verdict"] == "Do-Not-Install"
                                     for r in burns),
        "burns_flagged_at_least_caution": sum(
            SEVERITY[r["actual_verdict"]] >= 1 for r in burns),
        "clean_controls": len(cleans),
        "clean_false_positives": sum(r["actual_verdict"] != "Safe"
                                     for r in cleans),
        "caution_fixtures": len(cautions),
        "cautions_matched": sum(r["outcome"] == "MATCH" for r in cautions),
        "misses": [r["fixture"] for r in results
                   if r["outcome"] == "MISS (under-detected)"],
        "over_fires": [r["fixture"] for r in results
                       if r["outcome"] == "OVER-FIRE (over-detected)"],
    }
    out = {"summary": summary, "results": results}
    (HERE / "results.json").write_text(json.dumps(out, indent=1))

    for r in results:
        mark = {"MATCH": "  MATCH ", "MISS (under-detected)": "**MISS**",
                "OVER-FIRE (over-detected)": "*OVER** "}[r["outcome"]]
        print(f"{mark} {r['fixture']:28s} expected={r['expected_verdict']:15s} "
              f"actual={r['actual_verdict']:15s} rules={r['rules_fired']}")
    print("\nSUMMARY:", json.dumps(summary, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
