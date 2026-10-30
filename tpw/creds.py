"""Verifiable-credential-shaped documents, HMAC-signed by the issuer.

Credential types (design of record, credential schemas v1.0):
  ControllerLinkageCredential - binds an agent DID to a verified identity
    token. 24h expiry. evidence.verificationMethod names the rail honestly:
    "stand-in-verifier" until Moltbook early access lands, then
    "moltbook-verify-identity". The token itself is never stored - only its
    SHA-256 fingerprint.
  AuditVerdictCredential - bound to a package hash; every finding MUST carry
    {ruleId, severity, citation{file, line, quote}, summary}. A finding
    without a citation cannot be issued - enforced here, at issuance.
  DeliveryCredential - 9 rendition outputs {format, language, aspect,
    sha256}, the QC object, and a single-use settlementNonce. Permanent.

Signatures are HMAC-SHA256 over canonical JSON with a project key that
lives only in the state directory (0600). This is a demo-grade signature
scheme and is labeled as such; the verification logic (canonicalization,
expiry, nonce consumption) is the production logic.
"""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

ISSUER = "did:web:demo.trustproofwork.local:issuer"
SIG_TYPE = "HmacSha256Signature2026 (demo-grade)"


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


class KeyStore:
    def __init__(self, state_dir: Path):
        self.path = Path(state_dir) / "signing.key"
        if self.path.exists():
            self.key = bytes.fromhex(self.path.read_text().strip())
        else:
            self.key = os.urandom(32)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(self.key.hex())
            os.chmod(self.path, 0o600)

    def sign(self, body: dict) -> str:
        msg = json.dumps(body, sort_keys=True).encode()
        return hmac.new(self.key, msg, hashlib.sha256).hexdigest()


def did_for(agent_id: str) -> str:
    return f"did:web:demo.trustproofwork.local:agents:{agent_id}"


def did_document(agent_id: str) -> dict:
    did = did_for(agent_id)
    return {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "controller": did,
        "verificationMethod": [{
            "id": f"{did}#key-1", "type": "HmacSha256VerificationKey2026",
            "controller": did,
        }],
        "authentication": [f"{did}#key-1"],
        "service": [{"id": f"{did}#scorecard", "type": "TrustScorecard",
                     "serviceEndpoint": "local://scorecard"}],
    }


def _base(cred_type: str, subject: dict, expires: timedelta | None) -> dict:
    now = _now()
    cred = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": f"urn:tpw:cred:{secrets.token_hex(8)}",
        "type": ["VerifiableCredential", cred_type],
        "issuer": ISSUER,
        "issuanceDate": _iso(now),
        "credentialSubject": subject,
    }
    if expires is not None:
        cred["expirationDate"] = _iso(now + expires)
    return cred


def _finalize(ks: KeyStore, cred: dict) -> dict:
    cred["proof"] = {"type": SIG_TYPE, "created": cred["issuanceDate"],
                     "verificationMethod": f"{ISSUER}#key-1",
                     "proofValue": ks.sign(cred)}
    return cred


def verify(ks: KeyStore, cred: dict) -> tuple[bool, str]:
    """(ok, reason). Checks signature and expiry. Fail closed."""
    if not isinstance(cred, dict) or "proof" not in cred:
        return False, "not a credential / no proof"
    body = {k: v for k, v in cred.items() if k != "proof"}
    expect = ks.sign(body)
    if not hmac.compare_digest(expect, cred["proof"].get("proofValue", "")):
        return False, "signature invalid (forged or tampered)"
    exp = cred.get("expirationDate")
    if exp and _now() > _parse(exp):
        return False, f"credential expired at {exp}"
    return True, "valid"


def issue_linkage(ks: KeyStore, agent_id: str, token: str,
                  method: str, base_tier: int) -> dict:
    subject = {
        "id": did_for(agent_id),
        "agentId": agent_id,
        "baseTier": base_tier,
        "evidence": {
            "verificationMethod": method,
            "tokenFingerprintSha256": hashlib.sha256(token.encode()).hexdigest(),
        },
    }
    return _finalize(ks, _base("ControllerLinkageCredential", subject,
                               timedelta(hours=24)))


def issue_audit_verdict(ks: KeyStore, agent_id: str, skill_name: str,
                        package_hash: str, verdict: str,
                        findings: list[dict]) -> dict:
    for f in findings:
        cite = f.get("citation") or {}
        if not f.get("ruleId") or not f.get("severity") \
                or not cite.get("file") or not cite.get("line"):
            raise ValueError(
                "REFUSED: finding without ruleId/severity/citation "
                f"cannot be issued: {f!r}")
    subject = {
        "id": did_for(agent_id),
        "skill": skill_name,
        "packageHash": package_hash,
        "verdict": verdict,
        "findings": findings,
    }
    return _finalize(ks, _base("AuditVerdictCredential", subject,
                               timedelta(days=30)))


def issue_delivery(ks: KeyStore, agent_id: str, job_id: str,
                   outputs: list[dict], qc: dict) -> dict:
    for o in outputs:
        if not all(o.get(k) for k in ("format", "language", "aspect", "sha256")):
            raise ValueError(f"REFUSED: delivery output missing fields: {o!r}")
    subject = {
        "id": did_for(agent_id),
        "jobId": job_id,
        "outputs": outputs,
        "qc": qc,
        "settlementNonce": secrets.token_hex(16),
    }
    return _finalize(ks, _base("DeliveryCredential", subject, None))
