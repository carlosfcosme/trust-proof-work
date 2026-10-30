# Trust. Proof. Work.

An AI agent's trust, as a public record: who it is, what it runs, what it has delivered, what it was refused.

## Verify it yourself

```bash
python3 run_gate.py                # corpus gate + gauntlet benchmark (writes out/gate-report.json)
python3 tests/test_invariants.py   # escrow invariants I1-I6 (exit 0 = all pass)
python3 demo.py                    # the full 7-beat demo (writes out/scorecard.html, out/media/)
```

## Verified results (Oct 30, 2026)

| Check | Result |
|---|---|
| Golden corpus — 10 real skills, locked ground truth | **8 Safe / 2 Caution / 0 Do-Not-Install — exact match, gate PASS** |
| Gauntlet v1 — frozen baseline machinery (20 fixtures, verdicts locked 2026-10-21) | 13/20 exact, burns caught 3/6 |
| Gauntlet v1 — with the rule-fix layer | **20/20 exact, burns 6/6, clean false positives 0/8** |
| Gauntlet v2 — with the rule-fix layer (10 fixtures, locked 2026-10-21) | **10/10 exact** |
| Escrow invariants I1–I6 | **7/7 test groups pass** |
| Demo | 14/14 checks, 9 renditions QC-pass, settlement only on verified delivery |

---

# Trust. Proof. Work. — implementation

Agent-commerce trust stack for the Meta Global AI Hackathon (Startup
track, solo entrant Carlos Felipe Cosme). Built in-window, Oct 30, 2026,
on an NVIDIA DGX Spark.

**Trust** — identity handshake over a verifier adapter (stand-in rail
active; Moltbook early access pending), DID documents, controller-linkage
credentials, T0–T5 authority tiers.
**Proof** — a deterministic 5-check skill audit. The scanner and baseline
verdict mapper are the frozen audit machinery, vendored byte-identical in
`rig/` (audit_skill.py sha256 d5c687d9003f…). Verdicts are issued as
credentials; every finding must carry a file+line citation, enforced
mechanically by the interrogator contract and again at issuance.
**Work** — a paid content job: council ruling inside the tier envelope,
9 renditions produced and QC-verified (count, dimensions, SHA-256,
distinctness), a delivery credential, and escrow that settles only
against a valid, unconsumed delivery credential. Policy veto is final.

## Run it

```bash
python3 run_gate.py            # THE GATE + gauntlet benchmark (writes out/gate-report.json)
python3 tests/test_invariants.py   # I1–I6 invariant tests
python3 demo.py                # the 7-beat demo (writes out/scorecard.html, out/demo-transcript.json, out/media/)
```

## Measured results (Oct 30, 2026 — reproduced on the Spark)

- Corpus gate (10 real skills, locked ground truth): **8 Safe / 2 Caution /
  0 Do-Not-Install, exact match — PASS**
- Gauntlet v1 (20 synthetic fixtures, verdicts locked 2026-10-21):
  baseline frozen machinery **13/20 exact, burns 3/6** (identical to the
  2026-10-21 record) → with the rule-fix layer **20/20 exact, burns 6/6,
  clean false positives 0/8**
- Gauntlet v2 (10 fixtures, locked 2026-10-21): **10/10 exact** with fixes
- Invariants I1–I6: **all pass**
- Demo: **14/14 checks**, 9 renditions QC-pass, settlement on verified
  delivery; over-authority job, forged credential, and double settlement
  all denied with reasons

## Honest labels

- **Stand-in verifier** is the active identity rail and is labeled as
  such in every credential (`evidence.verificationMethod`). Moltbook
  approval is still pending; the swap is one adapter behind this
  interface and changes no tier logic.
- **Council seats are deterministic** unless a Meta Model API key is
  configured (`META_API_KEY` or `TPW_META_KEY_FILE`). With a key, seats
  are offered to Muse Spark (Standard tier only — contributor ids are
  refused in code) with deterministic fallback per seat. The corpus
  and gauntlet figures above are produced by the deterministic layers,
  which never call a model, at **$0.00 API spend**. Separately, a full
  demo run on the DGX with a live key had all three council seats
  served by Muse Spark 1.3 — decision approved 2–1, the risk seat's
  dissent on the record (3 model calls, 4,440 tokens).
- **Credential signatures are HMAC-SHA256** with a project key in the
  state directory — demo-grade signatures, production-shaped
  verification (canonical JSON, expiry, single-use nonces).
- **Renditions** in the demo job are rendered locally by ffmpeg as
  language/aspect title cards; in the full product the production pipeline
  produces them and Muse Image makes the covers. The delivery-credential
  contract is the same either way, and the demo transcript states which
  path produced a run's files.
- The frozen rig in `rig/` is never modified. All rule fixes live in
  `tpw/rulefixes.py` as a layer over its scan output.

## Terminology note

Two labels inside the frozen artifacts predate this repository's public
terminology: "Ep1" (the audit harness's original development label) and
"Day-4" (the sprint day the rule-fix layer was designed). They appear
only inside files that are preserved verbatim as evidence — the frozen
rig in `rig/` and the locked gauntlet records in `gauntlet/` (fixtures,
expected verdicts, and `RESULTS.md`) —
because those files are hash-verified exactly as they stand. Everywhere
this project speaks in its own voice, they read as "the audit machinery"
and "the rule-fix layer."
