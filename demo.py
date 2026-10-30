"""End-to-end demo: the seven beats, rehearsed and measured.

  1 identity handshake (stand-in verifier) -> linkage credential, tier T3
  2 audit of a Caution skill -> verdict credential -> tier drops to T1
  3 audit of a Safe skill -> verdict credential
  4 paid job inside authority -> council -> 9 renditions -> QC ->
    delivery credential -> escrow settles
  5 rogue beat: over-authority job denied; forged credential denied;
    double settlement denied
  6 counterfactual: a citation-less claim is refused by the interrogator
    and again at credential issuance; with enforcement off it would ship
  7 scorecard renders from the same state the demo just produced

Every figure printed is measured in this run. API status is reported as
found: if no Meta API key is configured, the council runs on its
deterministic seats and the transcript says so.
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "rig"))

import interrogator          # noqa: E402  (rig, frozen)
import verdicts as rig_verdicts  # noqa: E402  (rig, frozen)
import evidence              # noqa: E402  (rig, frozen)

from tpw import council2, creds, escrow as escrow_mod, meta_api, proof  # noqa: E402
from tpw import scorecard, tiers, verifier as verifier_mod, work  # noqa: E402

GAUNTLET = ROOT / "gauntlet" / "fixtures"
OUT = ROOT / "out"


def beat(n, title):
    print(f"\n[BEAT {n}] {title}")


def main() -> int:
    t0 = time.perf_counter()
    state = OUT / "state"
    if state.exists():
        shutil.rmtree(state)
    state.mkdir(parents=True)
    ks = creds.KeyStore(state)
    transcript = {"beats": [], "checks": []}

    def check(name, ok, detail=""):
        transcript["checks"].append({"check": name, "pass": bool(ok),
                                     "detail": detail})
        print(f"  {'PASS' if ok else 'FAIL'}  {name} {detail}")

    # ---- Beat 1: identity ---------------------------------------------
    beat(1, "Identity handshake (stand-in verifier - Moltbook pending)")
    ver = verifier_mod.StandInVerifier(state, state / "verifier-audit.jsonl")
    ver.register_agent("demo-agent", 3)
    token = ver.mint_token("demo-agent")
    v = ver.verify(token)
    linkage = creds.issue_linkage(ks, "demo-agent", token, v["method"], 3)
    agent = tiers.Agent("demo-agent", 3)
    print(f"  verified via {v['method']}; DID {creds.did_for('demo-agent')}")
    print(f"  linkage credential issued (24h); base tier T3 "
          f"(per-job ${agent.caps()['per_job']})")
    check("linkage credential verifies", creds.verify(ks, linkage)[0])
    try:
        ver.verify("tpw_forged-token")
        check("forged token rejected", False)
    except verifier_mod.VerificationFailed:
        check("forged token rejected (fail closed)", True)

    # ---- Beat 2: Caution audit -> tier drop ----------------------------
    beat(2, "Audit: mid-cdn-report -> Caution -> authority caps at T1")
    before = agent.caps()["per_job"]
    r1 = proof.audit(GAUNTLET / "mid-cdn-report", "mid-cdn-report",
                     "demo-agent", ks)
    agent.attach_verdict("mid-cdn-report", r1["verdict"])
    after = agent.caps()["per_job"]
    print(f"  verdict {r1['verdict']} (baseline {r1['baseline_verdict']}, "
          f"fixes {r1['fix_rules']}); credential {r1['status']}")
    print(f"  effective tier T{agent.effective_tier()}: per-job cap "
          f"${before} -> ${after}")
    check("caution verdict issued", r1["verdict"] == "Caution"
          and r1["credential"] is not None)
    check("tier drop T3 -> T1", agent.effective_tier() == 1 and after == 25)

    # ---- Beat 3: Safe audit --------------------------------------------
    beat(3, "Audit: clean-local-linter -> Safe")
    r2 = proof.audit(GAUNTLET / "clean-local-linter", "clean-local-linter",
                     "demo-agent", ks)
    agent.attach_verdict("clean-local-linter", r2["verdict"])
    print(f"  verdict {r2['verdict']}; credential {r2['status']}")
    check("safe verdict issued", r2["verdict"] == "Safe"
          and r2["credential"] is not None)

    # ---- Beat 4: job -> council -> work -> QC -> settle -----------------
    beat(4, "Job $20: council, production, QC, settlement")
    esc = escrow_mod.Escrow(state, ks)
    created = esc.create_job("job-001", agent, 20)
    check("job escrowed within authority", created["created"], created["reason"])
    deal = {"job_id": "job-001", "amount": 20, "market_value": 25}
    council = council2.rule(deal, agent, agent.skills,
                            spend_log=state / "spend-log.jsonl")
    for seat, vote in council["votes"].items():
        print(f"  council/{seat}: {vote['vote']} - {vote['reason']}")
    print(f"  council decision: {council['decision']} "
          f"(model: {council['model'] or 'deterministic seats - no API key'})")
    prod = work.produce("job-001", OUT / "media")
    print(f"  produced {prod['qc']['count']} renditions; QC pass "
          f"{prod['qc']['pass']} (dims {prod['qc']['dimensions_ok']}, "
          f"hashes {prod['qc']['hashes_ok']})")
    check("9 renditions QC pass", prod["qc"]["pass"])
    cred_outputs = [{k: o[k] for k in ("format", "language", "aspect", "sha256")}
                    for o in prod["outputs"]]
    dcred = creds.issue_delivery(ks, "demo-agent", "job-001",
                                 cred_outputs, prod["qc"])
    settled = esc.settle("job-001", dcred, council["decision"])
    print(f"  settlement: {settled}")
    check("escrow settled on delivery credential", settled["settled"])

    # ---- Beat 5: rogue ---------------------------------------------------
    beat(5, "Rogue: over-authority job, forged credential, double settle")
    rogue = esc.create_job("job-rogue", agent, 400)
    print(f"  $400 job at effective T1: {rogue}")
    check("over-authority job denied (I2)", not rogue["created"])
    esc.create_job("job-002", agent, 10)
    forged = json.loads(json.dumps(dcred))
    forged["credentialSubject"]["outputs"][0]["sha256"] = "0" * 64
    f_attempt = esc.settle("job-002", forged, "approve")
    print(f"  forged credential: {f_attempt}")
    check("forged credential denied (I1)", not f_attempt["settled"])
    again = esc.settle("job-001", dcred, "approve")
    print(f"  second settle of job-001: {again}")
    check("double settlement denied (I5)", not again["settled"])

    # ---- Beat 6: counterfactual ------------------------------------------
    beat(6, "Counterfactual: citation enforcement off vs on")
    skill_dir = GAUNTLET / "clean-local-linter"
    draft = rig_verdicts.verdict_for(skill_dir,
                                     evidence.scan_skill(skill_dir,
                                                         "clean-local-linter"))
    draft["claims"].append({"text": "clean-local-linter: phones home "
                                   "nightly with your notes",
                            "citation": None})
    val = interrogator.validate_draft(skill_dir, draft)
    print(f"  planted citation-less claim accepted by interrogator: "
          f"{val['accepted']} (rejections: "
          f"{[r['reason'] for r in val['rejections']]})")
    check("interrogator refuses citation-less claim", not val["accepted"])
    try:
        creds.issue_audit_verdict(
            ks, "demo-agent", "clean-local-linter", "sha256:x", "Safe",
            [{"ruleId": "SCAN", "severity": "info",
              "citation": None, "summary": "phones home nightly"}])
        check("issuance refuses citation-less finding", False)
    except ValueError as e:
        check("issuance refuses citation-less finding", True, str(e)[:60])
    off = proof.audit(GAUNTLET / "mid-cdn-report", "mid-cdn-report",
                      "demo-agent", ks, citation_enforcement=False)
    print(f"  enforcement OFF audit status: {off['status']} - the pipeline "
          f"ships without ever validating a claim")
    check("enforcement-off path labeled", off["status"] == "ISSUED_ENFORCEMENT_OFF")

    # ---- Beat 7: scorecard -------------------------------------------------
    beat(7, "Scorecard")
    gate_path = OUT / "gate-report.json"
    g = None
    if gate_path.exists():
        gr = json.loads(gate_path.read_text())
        g = {"baseline_exact": gr["gauntlet"]["baseline_exact"],
             "baseline_burns": gr["gauntlet"]["baseline_burns"],
             "after_exact": gr["gauntlet"]["after_exact"],
             "after_burns": gr["gauntlet"]["after_burns"],
             "after_clean_fp": gr["gauntlet"]["after_clean_fp"]}
    audits_view = []
    for r in (r1, r2):
        finds = r["credential"]["credentialSubject"]["findings"] \
            if r["credential"] else []
        audits_view.append({"skill": r["skill"], "verdict": r["verdict"],
                            "findings": finds})
    agent_view = {"did": creds.did_for("demo-agent"), "base_tier": 3,
                  "effective_tier": agent.effective_tier(),
                  "caps": agent.caps(),
                  "tier_note": "Caution skill mid-cdn-report caps authority "
                               "at T1 until a re-audit returns Safe or the "
                               "skill is removed."}
    html = scorecard.render(agent_view, audits_view,
                            [linkage, r1["credential"], r2["credential"],
                             dcred], gauntlet=g)
    (OUT / "scorecard.html").write_text(html)
    print(f"  scorecard written: {OUT / 'scorecard.html'}")

    transcript["elapsed_s"] = round(time.perf_counter() - t0, 2)
    transcript["meta_api"] = {"available": meta_api.available(),
                              "spark_model": council["model"],
                              "note": "no key configured - deterministic "
                                      "seats ran; $0.00 API spend this run"
                                      if not meta_api.available() else
                                      "live Spark seats used where parsed"}
    (OUT / "demo-transcript.json").write_text(json.dumps(transcript, indent=1))
    failed = [c for c in transcript["checks"] if not c["pass"]]
    print(f"\nDemo complete in {transcript['elapsed_s']}s - "
          f"{len(transcript['checks']) - len(failed)}/{len(transcript['checks'])} "
          f"checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
