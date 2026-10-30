"""Council: three seats (risk / value / compliance) ruling inside the
policy envelope. Majority decides; the escrow's Policy veto is final
regardless of the council outcome.

Default seats are deterministic. When a Meta API key is configured, the
seats are offered to Muse Spark first (strict JSON votes, parsed and
validated); any failure falls back to the deterministic seat. Spark is
never asked about, and cannot move, the envelope itself.
"""
import json

from . import meta_api


def _seat_risk(deal, agent, verdicts_map):
    cap = agent.caps()["per_job"]
    dni = [s for s, v in verdicts_map.items() if v == "Do-Not-Install"]
    caut = [s for s, v in verdicts_map.items() if v == "Caution"]
    if dni:
        return "reject", f"counterparty carries Do-Not-Install skill(s): {dni}"
    if cap is not None and deal["amount"] > cap:
        return "reject", f"amount {deal['amount']} exceeds effective per-job cap {cap}"
    if caut and cap is not None and deal["amount"] > 0.5 * cap:
        return "reject", f"caution skill(s) {caut}; amount > 50% of cap {cap}"
    if caut:
        return "approve", f"caution skill(s) {caut} noted; amount within 50% of cap"
    return "approve", "no risk flags"


def _seat_value(deal, agent, verdicts_map):
    if deal["amount"] <= deal["market_value"]:
        return "approve", f"amount {deal['amount']} <= market value {deal['market_value']}"
    return "counter", f"amount {deal['amount']} above market value {deal['market_value']}"


def _seat_compliance(deal, agent, verdicts_map):
    if agent.effective_tier() == 0:
        return "reject", "counterparty effective tier is 0 (unverified, frozen, or DNI-marked)"
    if any(v == "Do-Not-Install" for v in verdicts_map.values()):
        return "reject", "Do-Not-Install skill in counterparty set"
    return "approve", "identity verified, no compliance bar"


_SEATS = {"risk": _seat_risk, "value": _seat_value, "compliance": _seat_compliance}


def _spark_vote(seat: str, deal, agent, verdicts_map, model: str, spend_log):
    prompt = (
        f"You are the {seat} seat of a deal council for an agent marketplace. "
        f"Deal: amount ${deal['amount']}, market value ${deal['market_value']}, "
        f"job {deal['job_id']}. Counterparty effective tier "
        f"{agent.effective_tier()}, per-job cap {agent.caps()['per_job']}, "
        f"skill verdicts {verdicts_map}. Reply with ONLY a JSON object: "
        f"{{\"vote\": \"approve\"|\"reject\"|\"counter\", \"reason\": \"...\"}}")
    text = meta_api.chat(model, [{"role": "user", "content": prompt}],
                         spend_log=spend_log)
    obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
    if obj.get("vote") not in ("approve", "reject", "counter"):
        raise ValueError("invalid vote")
    return obj["vote"], str(obj.get("reason", ""))[:200] + " [spark seat]"


def rule(deal, agent, verdicts_map, spend_log=None) -> dict:
    model = meta_api.pick_spark_model() if meta_api.available() else None
    votes = {}
    for seat, fn in _SEATS.items():
        vote = None
        if model:
            try:
                vote = _spark_vote(seat, deal, agent, verdicts_map, model, spend_log)
            except Exception:
                vote = None  # fall back to the deterministic seat
        if vote is None:
            v, r = fn(deal, agent, verdicts_map)
            vote = (v, r + (" [deterministic seat]" if model else ""))
        votes[seat] = {"vote": vote[0], "reason": vote[1]}
    approvals = sum(1 for v in votes.values() if v["vote"] == "approve")
    return {"decision": "approve" if approvals >= 2 else "reject",
            "votes": votes, "model": model}
