"""T0-T5 authority tiers (tier table spec v1.0) and verdict effects.

Dollar figures are the demo envelope from the spec. Effects:
  Caution skill attached  -> authority capped at T1 until a re-audit returns
                             Safe or the skill is removed.
  Do-Not-Install attached -> effective T0 for value movement; the mark is
                             permanent on the scorecard.
  Owner freeze            -> effective T0 immediately, all activity halts.
  Upheld disputes         -> 1: one tier down for 30 days; 2: T0 + review.
"""
TIERS = {
    0: {"per_job": 0,     "per_day": 0,     "subcontract": 0},
    1: {"per_job": 25,    "per_day": 50,    "subcontract": 0},
    2: {"per_job": 100,   "per_day": 300,   "subcontract": 0},
    3: {"per_job": 500,   "per_day": 2000,  "subcontract": 100},
    4: {"per_job": 2500,  "per_day": 10000, "subcontract": 500},
    5: {"per_job": None,  "per_day": None,  "subcontract": None},  # owner-granted
}


class Agent:
    def __init__(self, agent_id: str, base_tier: int):
        self.agent_id = agent_id
        self.base_tier = base_tier
        self.skills: dict[str, str] = {}   # skill name -> verdict
        self.frozen = False
        self.disputes_upheld = 0
        self.dni_marked: set[str] = set()  # permanent scorecard marks

    def attach_verdict(self, skill: str, verdict: str):
        self.skills[skill] = verdict
        if verdict == "Do-Not-Install":
            self.dni_marked.add(skill)

    def effective_tier(self) -> int:
        if self.frozen:
            return 0
        if self.disputes_upheld >= 2:
            return 0
        t = self.base_tier
        if self.disputes_upheld == 1:
            t = max(0, t - 1)
        if any(v == "Do-Not-Install" for v in self.skills.values()):
            return 0
        if any(v == "Caution" for v in self.skills.values()):
            t = min(t, 1)
        return t

    def caps(self) -> dict:
        return TIERS[self.effective_tier()]
