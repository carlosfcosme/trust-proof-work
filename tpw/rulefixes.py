"""Day-4 rule fixes, layered OVER the frozen rig (the rig is never edited).

Implements the gauntlet findings F-G1..F-G6 from gauntlet/RESULTS.md:
  R-EXFIL      (F-G1) script reads credential-class paths AND calls an
               undeclared host -> critical; credential reads alone -> warning.
  R-UPDATE     (F-G2) check-5 update mechanism that APPLIES changes:
               disclosed in SKILL.md -> warning; silent -> critical.
               Consent-first + signature-verified channels do not fire.
  R-PS         (F-G3) PowerShell download-execute (iwr | iex and kin) in
               any file -> critical.
  R-UNDECLARED (F-G4) a script calls a host SKILL.md never declares ->
               warning (critical when combined with credential reads).
  R-VAULT      (F-G5) credential store + key material co-located and read
               by shipped code -> warning.
  R-B64-NOEXEC (F-G6) base64 blob with no decode->execute path in the
               package -> baseline DNI-B64 is downgraded to Caution.

Every finding carries a file+line citation or it is not emitted.
"""
import re
from pathlib import Path

CRED_PATH_RE = re.compile(
    r"(~/\.ssh|\.aws/credentials|\.env\b|id_rsa|id_ed25519|keychain|\.gnupg|/credentials\b)")
NET_LINE_RE = re.compile(r"(requests\.|urllib|curl |wget |fetch\(|axios|http\.client|socket\.)")
PS_EXEC_RE = re.compile(
    r"(iwr|Invoke-WebRequest|Invoke-Expression|\biex\b|powershell|pwsh)[^\n]*(\||https?://)", re.I)
PS_PIPE_RE = re.compile(r"\|\s*(iex|Invoke-Expression|powershell|pwsh)", re.I)
APPLY_RE = re.compile(r"(git pull|pip install --upgrade|pip install -U|curl[^\n]*-o |wget[^\n]*-O )")
EXEC_SINK_RE = re.compile(r"(\bexec\(|\beval\(|subprocess|os\.system|popen|__import__|\bcompile\()")
VAULT_FILE_RE = re.compile(r"^(vault\..*|.*\.(key|pem))$", re.I)
# v2-deck-driven general rules (locked deck, expected verdicts pre-registered):
CONCEAL_RE = re.compile(
    r"(do not mention|don't mention|do not tell|quietly|silently|"
    r"in the background|without telling|never tell)", re.I)
SRI_RE = re.compile(r"(integrity\s*=|sha384-|sha512-|sha256-[A-Za-z0-9+/=]{20,})")
PERSIST_RE = re.compile(r"(crontab|schtasks|systemd.*\.timer|LaunchAgents|@reboot)")
DNS_RE = re.compile(r"(gethostbyname|nslookup|\bdig\s|dns\.resolver|getaddrinfo)")
DYN_HOST_RE = re.compile(r"(f\"[^\"]*\{|f'[^\']*\{|\+ *[\"']\.|\.format\(|%s)")
INDEX_RE = re.compile(r"(--extra-index-url|--index-url|-i\s+https?://)")
STD_INDEX_HOSTS = ("pypi.org", "files.pythonhosted.org", "registry.npmjs.org")
TELEMETRY_HOST_RE = re.compile(r"(metrics\.|telemetry\.|analytics\.|track\.|stats\.)")
# Same script-delivery CDN host list the baseline mapper uses (verdicts.py).
SCRIPT_CDN = {
    "cdn.tailwindcss.com", "cdn.jsdelivr.net", "unpkg.com",
    "cdnjs.cloudflare.com", "esm.sh", "cdn.esm.sh", "jsdelivr.net",
    "fastly.jsdelivr.net", "gcore.jsdelivr.net",
}


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def _cite(skill_dir: Path, rel: str, pattern: re.Pattern):
    p = skill_dir / rel
    if not p.exists():
        return None
    for i, line in enumerate(_read(p).splitlines(), 1):
        if pattern.search(line):
            return {"file": rel, "line": i, "quote": line.strip()[:160]}
    return None


def _finding(rule, severity, citation, summary):
    if citation is None:
        return None
    return {"ruleId": rule, "severity": severity,
            "citation": citation, "summary": summary}


def apply_fixes(skill_dir: Path, scan: dict) -> dict:
    skill_dir = Path(skill_dir)
    scripts = list(scan["check3_code"].get("scripts", []))
    netcall_files = set(scan["check2_network"].get("netcall_files", []))
    url_hosts = {host: files for host, files in scan["check2_network"].get("urls", [])}

    skill_md = ""
    for p in skill_dir.rglob("SKILL.md"):
        skill_md = _read(p)
        break
    skill_md_l = skill_md.lower()

    script_text = {rel: _read(skill_dir / rel) for rel in scripts}
    findings: list[dict] = []
    downgrade_b64 = False

    # ---- R-PS (any file, incl. SKILL.md) --------------------------------
    all_files = [str(p.relative_to(skill_dir)) for p in skill_dir.rglob("*")
                 if p.is_file() and p.suffix.lower() in (".md", ".sh", ".ps1", ".py", ".js")]
    for rel in all_files:
        text = _read(skill_dir / rel)
        if PS_PIPE_RE.search(text) or ("iex" in text.lower() and PS_EXEC_RE.search(text)):
            cite = _cite(skill_dir, rel, PS_EXEC_RE) or _cite(skill_dir, rel, PS_PIPE_RE)
            f = _finding("R-PS", "critical", cite,
                         "PowerShell download-and-execute pattern "
                         "(iwr/Invoke-WebRequest piped to iex) - the POSIX "
                         "runtime-download rule's dialect blind spot (F-G3).")
            if f:
                findings.append(f)
                break

    # ---- R-EXFIL / R-UNDECLARED -----------------------------------------
    for rel, text in script_text.items():
        cred_lines = CRED_PATH_RE.search(text)
        hosts_here = [h for h, files in url_hosts.items() if rel in files]
        undeclared = [h for h in hosts_here if h not in skill_md]
        if cred_lines and rel in netcall_files and undeclared:
            cite = _cite(skill_dir, rel, NET_LINE_RE) or _cite(skill_dir, rel, CRED_PATH_RE)
            f = _finding("R-EXFIL", "critical", cite,
                         f"Script reads credential-class paths and sends to "
                         f"undeclared host(s) {undeclared} (F-G1).")
            if f:
                findings.append(f)
        elif cred_lines and rel not in netcall_files:
            cite = _cite(skill_dir, rel, CRED_PATH_RE)
            f = _finding("R-EXFIL-READ", "warning", cite,
                         "Script reads credential-class paths; no network "
                         "call in this file (F-G1 second clause).")
            if f:
                findings.append(f)
        elif undeclared and rel in netcall_files:
            cite = _cite(skill_dir, rel, NET_LINE_RE)
            sev = "warning"
            f = _finding("R-UNDECLARED", sev, cite,
                         f"Script calls host(s) {undeclared} never declared "
                         f"in SKILL.md (F-G4).")
            if f:
                findings.append(f)

    # ---- R-UPDATE ---------------------------------------------------------
    for rel in scan["check5_update"].get("update_hits", []):
        text = _read(skill_dir / rel)
        if not APPLY_RE.search(text) and rel not in script_text:
            # check-5 can flag SKILL.md prose; an applying script is required
            if not APPLY_RE.search(text):
                continue
        combined = (skill_md + "\n" + text).lower()
        verified_consent = ("signature" in combined or "verifies" in combined) \
            and ("asks before" in combined or "consent" in combined
                 or "changelog" in combined)
        if verified_consent:
            continue  # signed, consent-first channel: the v2 clean pattern
        # F-G2 names the concealment signals explicitly: "do not mention",
        # runs automatically, SKILL.md silent. Any concealment marker makes
        # it critical even if updates are mentioned in passing.
        concealed = bool(CONCEAL_RE.search(skill_md)) \
            or ("updat" not in skill_md_l and "pull" not in skill_md_l)
        cite = _cite(skill_dir, rel, APPLY_RE) or _cite(
            skill_dir, rel, re.compile(r"(update|pull|upgrade)", re.I))
        if not concealed:
            f = _finding("R-UPDATE", "warning", cite,
                         "Update mechanism applies changes automatically; "
                         "disclosed in SKILL.md (F-G2).")
        else:
            f = _finding("R-UPDATE", "critical", cite,
                         "Update mechanism applies changes with concealment "
                         "signals (undisclosed, or SKILL.md instructs that "
                         "it not be mentioned) - a hidden code-replacement "
                         "channel (F-G2).")
        if f:
            findings.append(f)

    # ---- R-VAULT ----------------------------------------------------------
    vault_files = [str(p.relative_to(skill_dir)) for p in skill_dir.rglob("*")
                   if p.is_file() and VAULT_FILE_RE.match(p.name)
                   and p.suffix.lower() not in (".md",)]
    if vault_files:
        for rel, text in script_text.items():
            for vf in vault_files:
                if Path(vf).name in text:
                    cite = _cite(skill_dir, rel, re.compile(re.escape(Path(vf).name)))
                    f = _finding("R-VAULT", "warning", cite,
                                 f"Credential/key material {vault_files} "
                                 f"co-located in the package and read by "
                                 f"shipped code (F-G5).")
                    if f:
                        findings.append(f)
                    break
            else:
                continue
            break

    # ---- v2-driven general rules -----------------------------------------
    suppress: set[str] = set()
    # R-CDN-SRI: a script-CDN load pinned by an SRI hash is the accepted-
    # safe pattern; suppress the baseline R-CDN rule when the package
    # carries an integrity pin for a CDN host it loads.
    if any(host in SCRIPT_CDN for host in url_hosts):
        for p in skill_dir.rglob("*"):
            if p.is_file() and SRI_RE.search(_read(p)):
                suppress.add("R-CDN")
                break
    for rel, text in script_text.items():
        # R-DNS-EXFIL: DNS resolution of dynamically built hostnames is a
        # covert exfiltration channel (data leaves in the query itself).
        if DNS_RE.search(text) and DYN_HOST_RE.search(text):
            cite = _cite(skill_dir, rel, DNS_RE)
            f = _finding("R-DNS-EXFIL", "critical", cite,
                         "DNS lookups on dynamically constructed hostnames "
                         "- data can leave encoded in the queries "
                         "themselves, bypassing HTTP inspection.")
            if f:
                findings.append(f)
        # R-DEP-CONFUSION: installing from a non-standard package index
        # executes third-party code at install time under names that may
        # shadow internal packages.
        if INDEX_RE.search(text) and not any(h in text for h in STD_INDEX_HOSTS):
            cite = _cite(skill_dir, rel, INDEX_RE)
            f = _finding("R-DEP-CONFUSION", "critical", cite,
                         "Install uses a non-standard package index - "
                         "dependency-confusion / install-time code "
                         "execution surface.")
            if f:
                findings.append(f)
        # R-TELEMETRY: usage metrics leave the machine; authority-relevant
        # even when disclosed and content-free.
        if TELEMETRY_HOST_RE.search(text) and rel in netcall_files:
            cite = _cite(skill_dir, rel, NET_LINE_RE)
            f = _finding("R-TELEMETRY", "warning", cite,
                         "Script transmits usage telemetry to a metrics "
                         "endpoint.")
            if f:
                findings.append(f)
    # R-PERSIST: installing a scheduled/persistent execution mechanism.
    for rel in list(script_text) + ["SKILL.md"]:
        text = script_text.get(rel) or (
            _read(skill_dir / rel) if (skill_dir / rel).exists() else "")
        if text and PERSIST_RE.search(text) and "crontab" in text.lower():
            cite = _cite(skill_dir, rel, PERSIST_RE)
            f = _finding("R-PERSIST", "warning", cite,
                         "Package installs a persistent scheduled execution "
                         "entry (cron) - it keeps running after the session "
                         "ends.")
            if f:
                findings.append(f)
            break

    # ---- R-B64-NOEXEC (downgrade signal only) -----------------------------
    if scan["check3_code"].get("b64_hits"):
        has_sink = any(EXEC_SINK_RE.search(t) for t in script_text.values())
        if not has_sink:
            downgrade_b64 = True

    return {"findings": findings, "downgrade_b64": downgrade_b64,
            "suppress_rules": suppress}
