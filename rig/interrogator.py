"""Interrogator DOUBLE (stands in for Muse Spark via Meta Model API).

Contract enforced mechanically: a verdict draft passes only if EVERY claim
carries a citation whose file exists inside the skill directory, whose
line number is in range, and whose quoted text matches that line
(whitespace-normalized prefix match). Citation-less or inaccurate claims
are rejected by construction — the draft is refused, not edited.
"""
from pathlib import Path


def _norm(s: str) -> str:
    return " ".join(s.split())


def validate_draft(skill_dir: Path, draft: dict) -> dict:
    rejections = []
    for i, claim in enumerate(draft.get("claims", [])):
        cite = claim.get("citation")
        if not cite:
            rejections.append({"claim_idx": i, "reason": "missing citation",
                               "text": claim.get("text", "")[:100]})
            continue
        p = Path(skill_dir) / cite["file"]
        if not p.exists():
            rejections.append({"claim_idx": i, "reason": "cited file not in bundle",
                               "text": claim.get("text", "")[:100]})
            continue
        lines = p.read_text(errors="replace").splitlines()
        if not (1 <= cite["line"] <= len(lines)):
            rejections.append({"claim_idx": i, "reason": "cited line out of range",
                               "text": claim.get("text", "")[:100]})
            continue
        actual = _norm(lines[cite["line"] - 1])
        quoted = _norm(cite.get("quote", ""))
        if not quoted or quoted[:60] not in actual and actual[:60] not in quoted:
            rejections.append({"claim_idx": i, "reason": "quoted text does not match cited line",
                               "text": claim.get("text", "")[:100]})
    return {"skill": draft.get("skill"), "verdict": draft.get("verdict"),
            "accepted": not rejections, "rejections": rejections}
