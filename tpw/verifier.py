"""Identity verification adapter.

Active rail: the STAND-IN verifier (Moltbook early access still pending).
Contract (stand-in memo section 5): same interface as the Moltbook
verify-identity call, fail closed, our tier table decides tiers, returned
strings are hostile data (never executed, never trusted beyond the
fields below), no availability coupling, full audit logging, 1h token
expiry realism.

Swap path (if approval lands before Day 9, Nov 3): implement
MoltbookVerifier.verify against POST /api/v1/agents/verify-identity with
the moltdev_ key from the secret store, keep this interface, change one
config value. Nothing else in the system knows which rail answered; the
linkage credential records the rail in evidence.verificationMethod.
"""
import json
import secrets
import time
from pathlib import Path


class VerificationFailed(Exception):
    pass


class StandInVerifier:
    method = "stand-in-verifier"

    def __init__(self, state_dir: Path, audit_log: Path):
        self.dir = Path(state_dir) / "standin"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.tokens_path = self.dir / "tokens.json"
        self.audit_log = Path(audit_log)
        if not self.tokens_path.exists():
            self.tokens_path.write_text("{}")

    def _tokens(self) -> dict:
        return json.loads(self.tokens_path.read_text())

    def _save(self, tokens: dict):
        self.tokens_path.write_text(json.dumps(tokens, indent=1))

    def _log(self, event: dict):
        event["ts"] = int(time.time())
        with open(self.audit_log, "a") as f:
            f.write(json.dumps(event) + "\n")

    def register_agent(self, agent_id: str, base_tier: int):
        """Enrollment is an operator action (in production: the agent's
        Moltbook account standing). Stores the tier evidence record."""
        path = self.dir / "agents.json"
        agents = json.loads(path.read_text()) if path.exists() else {}
        agents[agent_id] = {"base_tier": base_tier, "status": "active"}
        path.write_text(json.dumps(agents, indent=1))

    def mint_token(self, agent_id: str) -> str:
        """Mirror of POST /agents/me/identity-token (1h expiry)."""
        tokens = self._tokens()
        token = "tpw_" + secrets.token_urlsafe(24)
        tokens[token] = {"agent_id": agent_id, "expires": int(time.time()) + 3600}
        self._save(tokens)
        self._log({"event": "mint", "agent_id": agent_id})
        return token

    def verify(self, token: str) -> dict:
        """Fail closed: unknown, expired, or revoked -> VerificationFailed."""
        tokens = self._tokens()
        rec = tokens.get(token)
        if rec is None:
            self._log({"event": "verify_denied", "reason": "unknown token"})
            raise VerificationFailed("unknown token")
        if time.time() > rec["expires"]:
            self._log({"event": "verify_denied", "reason": "expired token",
                       "agent_id": rec["agent_id"]})
            raise VerificationFailed("token expired")
        agents = json.loads((self.dir / "agents.json").read_text()) \
            if (self.dir / "agents.json").exists() else {}
        arec = agents.get(rec["agent_id"])
        if arec is None or arec.get("status") != "active":
            self._log({"event": "verify_denied", "reason": "agent not active",
                       "agent_id": rec["agent_id"]})
            raise VerificationFailed("agent not active")
        self._log({"event": "verify_ok", "agent_id": rec["agent_id"]})
        return {"agent_id": rec["agent_id"], "base_tier": arec["base_tier"],
                "method": self.method}
