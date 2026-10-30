# Gauntlet Results — Frozen Ep1 Audit Machinery vs Methodology

**Run:** 2026-10-21, this VM. **Machinery:** `crews-test/meta/doubles/` read-only —
frozen scanner `audit_skill.py` (sha256 `d5c687d9003f…`, matches the crew-test
provenance record; untouched, mtime 2026-10-07) + deterministic verdict mapper
`verdicts.py`, imported exactly as `run_meta_test.py` imports them. No code in
the rig was read-modified, written, or retried against.

**Method:** 20 synthetic fixtures (authored from scratch for this gauntlet; no
real skill content). Expected verdicts are methodology judgments registered in
`expected.json` *before* the first run, grounded in the Ep1 audit semantics
(8/2/0 corpus). The runner executes scan + verdict per fixture and compares.
A divergence is a finding about the machinery. Fixtures and expectations were
not tuned after the run.

**Runner bug found and fixed transparently:** the first run's evidence summary
omitted the `check1_permissions.hooks_mentions` field (a reporting omission in
`run_gauntlet.py` only — verdicts were unaffected). Fixed, full gauntlet
re-run; outcomes identical, evidence recall now complete.

---

## Headline numbers

| Metric | Result |
|---|---|
| Fixtures run / machinery failures | 20 / 0 |
| Exact verdict matches | **13 / 20 (65%)** |
| Scanner evidence recall (planted properties surfaced somewhere in the scan) | **23 / 23 (100%)** |
| Burn detection (DNI expected → DNI actual) | **3 / 6 (50%)** |
| Burns flagged at all (≥ Caution) | 3 / 6 — the 3 missed burns scored fully **Safe** |
| Clean-control false positives (Safe expected → anything else) | **0 / 8 (0%)** |
| Caution accuracy (expected → actual) | 2 / 6 matched · 3 under-fired to Safe · 1 over-fired to DNI |

**The one-line truth the sprint plan's benchmark table can carry:** the scanner
sees everything; the verdict mapper rules on less than half of it. Every
missed burn below had its evidence sitting in the scan report — no mapper rule
consumed it.

## Per-fixture results

| Fixture | Category | Expected | Actual | Rules fired | Outcome |
|---|---|---|---|---|---|
| burn-curl-pipe-shell | burn | DNI | DNI | DNI-RTD | MATCH |
| burn-b64-payload | burn | DNI | DNI | DNI-B64, DNI-EVAL | MATCH |
| burn-eval-loader | burn | DNI | DNI | DNI-EVAL | MATCH |
| burn-ssh-exfil-requests | burn | DNI | **Safe** | — | **MISS** → F-G1 |
| burn-silent-self-update | burn | DNI | **Safe** | — | **MISS** → F-G2 |
| burn-powershell-iex | burn | DNI | **Safe** | — | **MISS** → F-G3 |
| clean-markdown-coach | clean | Safe | Safe | — | MATCH |
| clean-local-linter | clean | Safe | Safe | — | MATCH |
| clean-api-declared | clean | Safe | Safe | — | MATCH |
| clean-docs-sensitive-words | clean | Safe | Safe | — | MATCH |
| clean-vendored-report | clean | Safe | Safe | — | MATCH |
| clean-hook-announcer | clean | Safe | Safe | — | MATCH |
| mid-cdn-report | middle | Caution | Caution | R-CDN | MATCH |
| mid-bash-wildcard | middle | Caution | Caution | R-BASH | MATCH |
| mid-eval-in-docs | middle | Safe | Safe | — | MATCH (true negative: prose eval hits excluded from DNI-EVAL, as designed) |
| mid-cdn-font-css | middle | Safe | Safe | — | MATCH (true negative: R-CDN is script-host specific, as designed) |
| mid-vault-adjacent-key | middle | Caution | **Safe** | — | **MISS** → F-G5 |
| mid-undeclared-api-call | middle | Caution | **Safe** | — | **MISS** → F-G4 |
| mid-declared-updater | middle | Caution | **Safe** | — | **MISS** → F-G2 |
| mid-b64-benign | middle | Caution | **DNI** | DNI-B64 | **OVER-FIRE** → F-G6 |

## Findings (each is a proposed sprint-Day-4 rule fix; none applied — the frozen rig stays frozen)

- **F-G1 (critical) — No exfiltration rule.** `burn-ssh-exfil-requests` had its
  undeclared exfil host in `check2.urls`, the POST in `netcall_files`, and
  three credential-class + two home refs in check 4 — and scored Safe.
  *Proposed R-EXFIL:* a script that reads credential-class paths
  (`~/.ssh`, `.aws/credentials`, `.env`, keychain) AND makes a network call
  to a host not declared in SKILL.md → Do-Not-Install; credential-path reads
  with no network → Caution.
- **F-G2 (critical) — Check 5 is verdict-blind.** `update_hits` fired for both
  `burn-silent-self-update` (hidden) and `mid-declared-updater` (fully
  disclosed) — no verdict rule reads check 5, so both scored identically Safe,
  and the mapper cannot distinguish a silent code-replacement channel from a
  disclosed, opt-out update. *Proposed R-UPDATE:* an update mechanism present
  → at least Caution; update mechanism + concealment ("do not mention",
  runs automatically, SKILL.md silent) → Do-Not-Install.
- **F-G3 — Download-execute detection is POSIX-only in check 3.**
  `burn-powershell-iex`'s `iwr <url> | iex` was caught by check 5's own regex
  (`update_hits` on SKILL.md) but check 3's runtime-download pattern requires
  pipe-to-(ba)sh. Same hostile property, different shell dialect, Safe score.
  *Proposed:* extend the RTD pattern to pipe-to-`iex`/`powershell` (or unify
  the check-5 pattern with check 3 and route it to a verdict rule).
- **F-G4 — No declared-vs-actual destination diff.** `clean-api-declared` and
  `mid-undeclared-api-call` run near-identical code; one discloses the host,
  the other asserts it is "fully offline." The mapper scores both Safe —
  SKILL.md declarations are never parsed into an allowlist.
  *Proposed R-UNDECLARED:* network hosts in code absent from SKILL.md text →
  Caution (Do-Not-Install when combined with F-G1 signals).
- **F-G5 — Credential-vault co-location invisible.** The vault fixture's
  credential material surfaced in check 4, but check-4 evidence never moves a
  verdict. The corpus's real vault case (agent-browser) reached Caution only
  via its unrelated R-BASH side door — this fixture, deliberately built
  without the wildcard, exposes the gap.
  *Proposed R-VAULT:* credential store + key material co-located in the same
  package → Caution (mirrors the human Ep1 verdict on agent-browser).
- **F-G6 (over-fire) — DNI-B64 has no execution-path requirement.**
  `mid-b64-benign` (a disclosed plain-text template, decoded and printed,
  never executed) convicts identically to the real payload fixture.
  *Proposed:* DNI-B64 requires a decode→execute or decode→write-executable
  path in the package; a blob with no execution path → Caution (encoded
  content still must be decoded to be audited).

## What held up (defensive value)

- **False-positive control:** 0/8 clean controls flagged. The prose-keyword
  fixture (`clean-docs-sensitive-words`) confirmed the Ep1 design call —
  check-4 keyword hits in prose never move a verdict.
- **True negatives where designed:** prose-only `eval` mentions excluded from
  DNI-EVAL (script-file scoping works); non-script CDN hosts excluded from
  R-CDN (host-list scoping works).
- **The classical payload surface is fully covered:** curl-pipe-shell,
  base64-payload-with-exec, and direct eval-in-script all convicted on the
  correct rules with citations the Interrogator can validate.

## Caveats (carry into the submission's benchmark table)

- Expected verdicts are one auditor's methodology judgments, fixed before the
  run — the gauntlet measures the frozen mapper, not an absolute ground truth.
- The run measures scanner + mapper only. The Interrogator citation checker
  (a labeled test double, not frozen machinery) is covered by the crew test,
  not this gauntlet.
- Suggested table for the submission: 3/6 burns detected as DNI (50%), 3/6
  burns scoring Safe (all named), 0/8 clean false positives, plus the fix list
  — the judges' table rewards the honesty of the miss column, and the sprint
  Day-4 fixes turn this table into a before/after.
