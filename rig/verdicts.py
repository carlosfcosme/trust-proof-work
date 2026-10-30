"""Deterministic verdict mapper + claim generator (Audit Runner -> Interrogator).

Verdict rules (fixed before the run; derived from the Ep1 methodology in
agent-security-audit-ep01-verified-findings.md):

  DNI (Do-Not-Install) if the scan shows any of:
    - b64_hits (long base64 blobs decoding to ASCII payloads), or
    - runtime_download_hits (curl|sh style payload fetch), or
    - eval-style execution hits inside real script files.
  Caution if either:
    R-CDN  a script-delivery CDN host appears in check2 urls (generated
           artifacts would load remote JS at view time), or
    R-BASH check1 tools_mentions grants Bash(<tool>:*) — unrestricted
           shell wildcard to one tool.
  Safe otherwise. (Bare keyword hits in prose — check4 sensitive_hits —
  never move a verdict on their own; the Ep1 audit verified those in
  context as documentation examples.)

Every claim produced carries a file+line citation into the skill's own
files so the Interrogator double can validate it mechanically.
"""
from pathlib import Path
import re

from evidence import find_line, find_line_re, find_b64_line

# Scanner hit formats (audit_skill.py) that verdicts.py resolves to lines:
#   eval_hits:             "{rel}:{token}"
#   b64_hits:              "{rel}: {n} chars, decodes to ASCII: {prefix!r}"
#   runtime_download_hits: "{rel}"   (pattern: (curl|wget|iwr).*| (ba)?sh)
RTD_RE = re.compile(r"(curl|wget|iwr).*\|\s*(ba)?sh", re.I)
B64_HIT_RE = re.compile(r"^(.*?): (\d+) chars, decodes to ASCII")

SCRIPT_CDN_HOSTS = {
    "cdn.tailwindcss.com", "cdn.jsdelivr.net", "unpkg.com",
    "cdnjs.cloudflare.com", "esm.sh", "cdn.esm.sh", "jsdelivr.net",
    "fastly.jsdelivr.net", "gcore.jsdelivr.net",
}


def _cite(skill_dir, rel, needle, fallback_needle=None):
    hit = find_line(skill_dir, rel, needle)
    if hit is None and fallback_needle:
        hit = find_line(skill_dir, rel, fallback_needle)
    if hit is None:
        return None
    line, text = hit
    return {"file": rel, "line": line, "quote": text[:160]}


def verdict_for(skill_dir: Path, scan: dict) -> dict:
    name = scan["skill"]
    claims = []
    rules_fired = []

    c3 = scan["check3_code"]
    if c3["b64_hits"]:
        rules_fired.append("DNI-B64")
        hit = c3["b64_hits"][0]
        cite = None
        m = B64_HIT_RE.match(hit)
        if m:
            found = find_b64_line(skill_dir, m.group(1), int(m.group(2)))
            if found:
                line, text = found
                cite = {"file": m.group(1), "line": line, "quote": text[:160]}
        claims.append({"text": f"{name}: obfuscated base64 payload evidence: {hit}",
                       "citation": cite})
    if c3["runtime_download_hits"]:
        rules_fired.append("DNI-RTD")
        rel = c3["runtime_download_hits"][0]
        found = find_line_re(skill_dir, rel, RTD_RE)
        cite = ({"file": rel, "line": found[0], "quote": found[1][:160]}
                if found else None)
        claims.append({"text": f"{name}: runtime payload download in {rel}",
                       "citation": cite})
    script_evals = [h for h in c3["eval_hits"]
                    if any(h.startswith(s + ":") or h.startswith(s) for s in c3["scripts"])]
    if c3["scripts"] and script_evals:
        rules_fired.append("DNI-EVAL")
        hit = script_evals[0]
        rel, _, token = hit.rpartition(":")
        cite = _cite(skill_dir, rel, token) if rel and token else None
        claims.append({"text": f"{name}: dynamic execution in shipped script: {hit}",
                       "citation": cite})

    # R-CDN
    for host, files in scan["check2_network"]["urls"]:
        if host in SCRIPT_CDN_HOSTS:
            rules_fired.append("R-CDN")
            rel = files[0]
            cite = _cite(skill_dir, rel, host)
            claims.append({
                "text": f"{name}: generated artifacts load remote JavaScript from {host} (in {rel})",
                "citation": cite})

    # R-BASH
    for mention in scan["check1_permissions"].get("tools_mentions", []):
        if "Bash(" in mention and ":*)" in mention:
            rules_fired.append("R-BASH")
            smd = Path(scan["skill_md"]).name if scan.get("skill_md") else "SKILL.md"
            # scan.skill_md is the path as passed; resolve relative to skill_dir's parent chain
            rel = None
            for p in Path(skill_dir).rglob("*"):
                if p.name == smd and "allowed-tools" in p.read_text(errors="replace"):
                    rel = str(p.relative_to(skill_dir))
                    break
            cite = _cite(skill_dir, rel, "allowed-tools") if rel else None
            claims.append({
                "text": f"{name}: frontmatter grants unrestricted shell wildcard '{mention.strip()}'",
                "citation": cite})

    if any(r.startswith("DNI") for r in rules_fired):
        verdict = "Do-Not-Install"
    elif rules_fired:
        verdict = "Caution"
    else:
        verdict = "Safe"
        smd_rel = None
        for p in Path(skill_dir).rglob("SKILL.md"):
            smd_rel = str(p.relative_to(skill_dir))
            break
        cite = _cite(skill_dir, smd_rel, "name:") if smd_rel else None
        claims.append({
            "text": (f"{name}: 5-check scan clean — no payload, download, or "
                     f"dynamic-execution evidence; no script-CDN hosts; no "
                     f"shell-wildcard grants (files scanned: {scan['file_count']})"),
            "citation": cite})
    return {"skill": name, "verdict": verdict, "rules_fired": rules_fired,
            "claims": claims}
