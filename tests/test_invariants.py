"""Invariant tests I1-I6 (tier spec), executable without pytest.

Run: python3 tests/test_invariants.py  (exit 0 = all pass)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tpw import creds, escrow as escrow_mod, tiers  # noqa: E402


def fresh():
    td = tempfile.mkdtemp()
    ks = creds.KeyStore(Path(td))
    return ks, escrow_mod.Escrow(Path(td), ks)


def delivery(ks, job, qc_pass=True):
    outs = [{"format": "mp4", "language": "EN", "aspect": "16:9",
             "sha256": "a" * 64}]
    return creds.issue_delivery(ks, "agent", job, outs,
                                {"count": 9, "pass": qc_pass})


def main() -> int:
    fails = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            fails.append(name)

    # I2: no authorization above effective authority
    ks, esc = fresh()
    a = tiers.Agent("agent", 3)
    check("I2 job above T3 per-job cap denied",
          not esc.create_job("j1", a, 501)["created"])
    check("I2 job at cap allowed", esc.create_job("j2", a, 500)["created"])

    # I3: Caution caps authority at T1
    a.attach_verdict("s1", "Caution")
    check("I3 caution caps per-job at $25",
          not esc.create_job("j3", a, 26)["created"]
          and esc.create_job("j4", a, 25)["created"])

    # I4: Do-Not-Install zeroes authority
    a.attach_verdict("s2", "Do-Not-Install")
    check("I4 DNI zeroes authority", not esc.create_job("j5", a, 1)["created"]
          and a.effective_tier() == 0)

    # I1: no settlement without a valid unconsumed delivery credential
    ks, esc = fresh()
    b = tiers.Agent("agent", 3)
    esc.create_job("job", b, 100)
    check("I1 settle with no credential denied",
          not esc.settle("job", None, "approve")["settled"])
    forged = delivery(ks, "job")
    forged["credentialSubject"]["outputs"][0]["sha256"] = "b" * 64
    check("I1 settle with forged credential denied",
          not esc.settle("job", forged, "approve")["settled"])
    qcfail = delivery(ks, "job", qc_pass=False)
    check("I1 settle with QC-fail credential denied",
          not esc.settle("job", qcfail, "approve")["settled"])
    good = delivery(ks, "job")
    check("happy path settles", esc.settle("job", good, "approve")["settled"])

    # I5: one settlement per job
    check("I5 second settle denied",
          not esc.settle("job", good, "approve")["settled"])
    other = delivery(ks, "job")
    check("I5 settle with fresh nonce on settled job denied",
          not esc.settle("job", other, "approve")["settled"])

    # I6: owner freeze halts everything
    ks, esc = fresh()
    c = tiers.Agent("agent", 4)
    c.frozen = True
    check("I6 frozen agent cannot create jobs",
          not esc.create_job("jx", c, 10)["created"])
    c.frozen = False
    esc.create_job("jy", c, 10)
    cred = delivery(ks, "jy")
    check("I6 frozen agent cannot settle",
          not esc.settle("jy", cred, "approve", seller_frozen=True)["settled"])

    print(f"\n{7 - len(fails)}/7 invariant groups pass"
          if not fails else f"\nFAILURES: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
