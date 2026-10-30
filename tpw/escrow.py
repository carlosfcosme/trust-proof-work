"""Escrow: sandbox settlement against delivery credentials.

Invariants (tier spec I1-I6), enforced here and exercised by
tests/test_invariants.py:
  I1 no settlement without a valid, unconsumed delivery credential
  I2 no job authorized above the seller's effective tier authority
  I3 a Caution verdict caps authority (via tiers.Agent.caps)
  I4 a Do-Not-Install verdict zeroes authority (via tiers.Agent)
  I5 one settlement per job (settlementNonce is consumed on settle)
  I6 an owner freeze halts everything immediately

Every decision, settle or deny, is appended to a JSONL ledger with its
reason - the same discipline as the rig's policy engine.
"""
import json
import time
from pathlib import Path

from . import creds


class Escrow:
    def __init__(self, state_dir: Path, ks: creds.KeyStore):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ks = ks
        self.jobs_path = self.dir / "jobs.json"
        self.used_nonces_path = self.dir / "used-nonces.json"
        self.ledger_path = self.dir / "escrow-ledger.jsonl"

    def _jobs(self) -> dict:
        return json.loads(self.jobs_path.read_text()) if self.jobs_path.exists() else {}

    def _save_jobs(self, jobs: dict):
        self.jobs_path.write_text(json.dumps(jobs, indent=1))

    def _nonces(self) -> list:
        return json.loads(self.used_nonces_path.read_text()) \
            if self.used_nonces_path.exists() else []

    def _log(self, entry: dict):
        entry["ts"] = int(time.time())
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def create_job(self, job_id: str, seller, amount: float,
                   day_total_before: float = 0.0) -> dict:
        def deny(reason):
            self._log({"action": "JOB_DENY", "job_id": job_id,
                       "amount": amount, "reason": reason})
            return {"created": False, "reason": reason}

        if seller.frozen:
            return deny("I6: seller is owner-frozen; all activity halted")
        caps = seller.caps()
        if caps["per_job"] is not None and amount > caps["per_job"]:
            return deny(f"I2: amount {amount} exceeds effective per-job cap "
                        f"{caps['per_job']} (tier {seller.effective_tier()})")
        if caps["per_day"] is not None \
                and day_total_before + amount > caps["per_day"]:
            return deny(f"I2: amount {amount} would exceed effective per-day "
                        f"cap {caps['per_day']}")
        jobs = self._jobs()
        jobs[job_id] = {"job_id": job_id, "seller": seller.agent_id,
                        "amount": amount, "status": "ESCROWED"}
        self._save_jobs(jobs)
        self._log({"action": "JOB_CREATE", "job_id": job_id, "amount": amount,
                   "seller": seller.agent_id,
                   "effective_tier": seller.effective_tier()})
        return {"created": True, "reason": "job escrowed within authority"}

    def settle(self, job_id: str, credential, council_decision: str,
               seller_frozen: bool = False) -> dict:
        def deny(reason):
            self._log({"action": "DENY", "job_id": job_id, "reason": reason})
            return {"settled": False, "reason": reason}

        if seller_frozen:
            return deny("I6: seller is owner-frozen; settlement halted")
        jobs = self._jobs()
        job = jobs.get(job_id)
        if job is None:
            return deny("unknown job")
        if job["status"] == "SETTLED":
            return deny("I5: job already settled")
        if council_decision != "approve":
            return deny(f"council decision is '{council_decision}', not approve")
        if credential is None:
            return deny("I1: no delivery credential presented")
        ok, why = creds.verify(self.ks, credential)
        if not ok:
            return deny(f"I1: delivery credential invalid - {why}")
        subj = credential.get("credentialSubject", {})
        if "DeliveryCredential" not in credential.get("type", []):
            return deny("I1: presented credential is not a DeliveryCredential")
        if subj.get("jobId") != job_id:
            return deny("I1: credential jobId does not match job")
        if not subj.get("qc", {}).get("pass"):
            return deny("delivery credential records QC FAIL")
        nonce = subj.get("settlementNonce")
        if not nonce or nonce in self._nonces():
            return deny("I1/I5: settlement nonce missing or already consumed")
        used = self._nonces()
        used.append(nonce)
        self.used_nonces_path.write_text(json.dumps(used))
        job["status"] = "SETTLED"
        self._save_jobs(jobs)
        self._log({"action": "SETTLE", "job_id": job_id,
                   "amount": job["amount"], "nonce": nonce})
        return {"settled": True, "reason": "settled on verified delivery credential"}
