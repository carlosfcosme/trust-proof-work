"""Identity Engineer DOUBLE — local stand-in verifier for the Moltbook
identity API (the same local fallback the production design specifies).
Fixture tokens -> DID documents -> tier assignment."""
import json
from pathlib import Path


class RevokedCredential(Exception):
    pass


class StandInVerifier:
    def __init__(self, fixtures_path: Path):
        data = json.loads(Path(fixtures_path).read_text())
        self._by_token = {i["token"]: i for i in data["identities"]}

    def verify(self, token: str) -> dict:
        rec = self._by_token.get(token)
        if rec is None:
            return {"did": None, "tier": 0, "status": "unknown",
                    "holder": None}
        if rec["status"] == "revoked":
            raise RevokedCredential(rec["did"])
        return {"did": rec["did"], "tier": rec["tier"],
                "status": rec["status"], "holder": rec["holder"]}
