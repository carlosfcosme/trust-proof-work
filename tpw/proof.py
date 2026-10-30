"""Proof layer: audit a skill package and issue its verdict credential.

Pipeline: frozen rig scan -> baseline verdict (rig verdicts.py) ->
Day-4 rule fixes (tpw.rulefixes) -> final verdict -> interrogator
citation validation (rig interrogator.py: every claim's citation must
resolve to a real file+line with matching text) -> credential issuance
(tpw.creds refuses citation-less findings at issuance).

The interrogator contract is mechanical: with citation_enforcement on,
a draft whose claims fail validation is REFUSED, not edited. The
counterfactual (enforcement off) exists to demonstrate, in the demo,
what the enforcement is worth.
"""
import hashlib
import sys
from pathlib import Path

RIG = Path(__file__).resolve().parent.parent / "rig"
sys.path.insert(0, str(RIG))

import evidence          # noqa: E402  (rig, frozen)
import interrogator      # noqa: E402  (rig, frozen)
import verdicts as rig_verdicts  # noqa: E402  (rig, frozen)

from . import creds, rulefixes  # noqa: E402

_SEV = {"Do-Not-Install": "critical", "Caution": "warning", "Safe": "info"}


def package_hash(skill_dir: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(skill_dir).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(skill_dir)).encode())
            h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()


def final_verdict(baseline: dict, fixes: dict) -> str:
    rules = set(baseline.get("rules_fired", []))
    rules -= set(fixes.get("suppress_rules", set()))
    if fixes["downgrade_b64"]:
        rules.discard("DNI-B64")
    if any(r.startswith("DNI") for r in rules):
        return "Do-Not-Install"
    if any(f["severity"] == "critical" for f in fixes["findings"]):
        return "Do-Not-Install"
    # F-G6: a base64 blob with no execution path is Caution, not Safe -
    # encoded content still must be decoded to be audited.
    if rules or fixes["findings"] or fixes["downgrade_b64"]:
        return "Caution"
    return "Safe"


def audit(skill_dir, name: str, agent_id: str, ks: creds.KeyStore,
          citation_enforcement: bool = True) -> dict:
    skill_dir = Path(skill_dir)
    scan = evidence.scan_skill(skill_dir, name)
    baseline = rig_verdicts.verdict_for(skill_dir, scan)
    fixes = rulefixes.apply_fixes(skill_dir, scan)
    verdict = final_verdict(baseline, fixes)

    # Interrogator validates the baseline draft's claims mechanically.
    inter = interrogator.validate_draft(skill_dir, baseline)

    findings: list[dict] = []
    for claim in baseline.get("claims", []):
        cite = claim.get("citation")
        if not cite:
            continue  # uncited claims never enter a credential
        rule = (baseline.get("rules_fired") or ["SCAN"])[0]
        findings.append({"ruleId": rule, "severity": _SEV[verdict],
                         "citation": {"file": cite["file"],
                                      "line": cite["line"],
                                      "quote": cite.get("quote", "")},
                         "summary": claim["text"]})
    findings.extend(fixes["findings"])

    result = {
        "skill": name, "verdict": verdict,
        "baseline_verdict": baseline["verdict"],
        "rules_fired": baseline.get("rules_fired", []),
        "fix_rules": sorted({f["ruleId"] for f in fixes["findings"]}),
        "suppressed_rules": sorted(fixes.get("suppress_rules", set())),
        "downgrade_b64": fixes["downgrade_b64"],
        "interrogation": inter,
        "package_hash": package_hash(skill_dir),
        "credential": None,
    }
    if citation_enforcement and not inter["accepted"]:
        result["status"] = "REFUSED_BY_INTERROGATOR"
        return result
    result["credential"] = creds.issue_audit_verdict(
        ks, agent_id, name, result["package_hash"], verdict, findings)
    result["status"] = "ISSUED" if citation_enforcement \
        else "ISSUED_ENFORCEMENT_OFF"
    return result
