#!/usr/bin/env python3
"""Five-check red-team audit harness for Claude Code skills (static pass).

Reads a skill directory and produces a structured findings report for:
  1. Permissions requested (frontmatter + manifests)
  2. Network surface (URLs / network calls in files)
  3. Code inspection (executable scripts: obfuscation, eval, runtime downloads)
  4. Data handling (reads beyond stated scope: keys, ssh, env)
  5. Update mechanism (self-update / remote code pull)

Usage: audit_skill.py <skill_dir> <skill_name>
Output: JSON report on stdout.
"""
import json, os, re, sys, base64

SKILL_DIR = sys.argv[1]
NAME = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(SKILL_DIR)

TEXT_EXTS = {'.md', '.txt', '.json', '.yaml', '.yml', '.sh', '.py', '.js',
            '.ts', '.mjs', '.cjs', '.rb', '.go', '.rs', '.toml', '.ini', '.cfg'}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build'}

def walk_files(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            p = os.path.join(dp, fn)
            out.append(p)
    return sorted(out)

def read_text(p, limit=2_000_000):
    try:
        if os.path.getsize(p) > limit:
            return None
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return None

def find_skill_md(root):
    for p in walk_files(root):
        if os.path.basename(p).lower() == 'skill.md':
            return p
    return None

def parse_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line and not line.startswith((' ', '\t')):
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm

URL_RE = re.compile(r'https?://[A-Za-z0-9._~:/?#@!$&\'()*+,;=%\[\]-]+')
NETCALL_RE = re.compile(r'\b(curl|wget|Invoke-WebRequest|fetch\(|axios\.|http\.get|https\.get|urllib|requests\.(get|post)|socket\.|WebSocket|nc\s+-|telnet)\b')
EVAL_RE = re.compile(r'\b(eval|exec|Function\(|child_process|popen|subprocess\.(run|call|Popen)|os\.system|shell_exec|new\s+VM|vm\.runIn)\b')
B64_RE = re.compile(r'[A-Za-z0-9+/]{120,}={0,2}')
SENSITIVE_RE = re.compile(r'(~\/\.ssh|\.ssh\/|id_rsa|id_ed25519|\.env\b|API[_-]?KEY|SECRET|TOKEN|passwd|shadow|\.aws\/credentials|\.gnupg|keychain|credential)', re.I)
UPDATE_RE = re.compile(r'(self[-_ ]?update|auto[-_ ]?update|check[-_ ]?for[-_ ]?updates?|latest.*release|npm\s+(install|update)|pip\s+install.*--upgrade|git\s+pull|curl.*\|\s*(ba)?sh|iwr.*\|\s*iex)', re.I)
HOME_RE = re.compile(r'(\$HOME|~\/|\/home\/|\/Users\/|%USERPROFILE%|os\.path\.expanduser|Path\.home)')

files = walk_files(SKILL_DIR)
report = {
    'skill': NAME,
    'dir': SKILL_DIR,
    'file_count': len(files),
    'check1_permissions': {},
    'check2_network': {'urls': [], 'netcall_files': []},
    'check3_code': {'scripts': [], 'eval_hits': [], 'b64_hits': [], 'runtime_download_hits': []},
    'check4_data': {'sensitive_hits': [], 'home_refs': []},
    'check5_update': {'update_hits': []},
}

# --- Check 1: permissions ---
smd = find_skill_md(SKILL_DIR)
report['skill_md'] = smd
if smd:
    text = read_text(smd) or ''
    fm = parse_frontmatter(text)
    report['check1_permissions']['frontmatter'] = fm
    # also look for explicit permission/tool mentions in body
    tools = re.findall(r'(?i)(?:allowed-tools|tools)\s*:\s*([^\n]+)', text)
    report['check1_permissions']['tools_mentions'] = tools[:5]
    # any hooks / commands declared
    hooks = re.findall(r'(?i)hooks?\s*:\s*([^\n]+)', text)
    report['check1_permissions']['hooks_mentions'] = hooks[:5]

# --- Checks 2-5: scan all text files ---
url_hosts = {}
for p in files:
    rel = os.path.relpath(p, SKILL_DIR)
    ext = os.path.splitext(p)[1].lower()
    if ext not in TEXT_EXTS:
        continue
    text = read_text(p)
    if text is None:
        continue
    # check 2
    for u in URL_RE.findall(text):
        host = re.sub(r'^https?://', '', u).split('/')[0].split(':')[0].split('?')[0]
        url_hosts.setdefault(host, set()).add(rel)
    if NETCALL_RE.search(text):
        report['check2_network']['netcall_files'].append(rel)
    # check 3
    if ext in {'.sh', '.py', '.js', '.ts', '.mjs', '.cjs', '.rb'} or 'script' in rel.lower():
        report['check3_code']['scripts'].append(rel)
    for m in EVAL_RE.finditer(text):
        report['check3_code']['eval_hits'].append(f"{rel}:{m.group(0)}")
    for m in B64_RE.finditer(text):
        blob = m.group(0)
        # only flag long blobs that decode cleanly (likely payloads, not hashes)
        try:
            dec = base64.b64decode(blob + '=' * (-len(blob) % 4))
            if len(dec) > 60 and all(32 <= b < 127 or b in (9, 10, 13) for b in dec[:200]):
                report['check3_code']['b64_hits'].append(f"{rel}: {len(blob)} chars, decodes to ASCII: {dec[:80]!r}")
        except Exception:
            pass
    if re.search(r'(curl|wget|iwr).*\|\s*(ba)?sh', text, re.I):
        report['check3_code']['runtime_download_hits'].append(rel)
    # check 4
    for m in SENSITIVE_RE.finditer(text):
        report['check4_data']['sensitive_hits'].append(f"{rel}: {m.group(0)}")
    for m in HOME_RE.finditer(text):
        report['check4_data']['home_refs'].append(f"{rel}: {m.group(0)}")
    # check 5
    if UPDATE_RE.search(text):
        report['check5_update']['update_hits'].append(rel)

report['check2_network']['urls'] = sorted(
    ((h, sorted(v)) for h, v in url_hosts.items()),
    key=lambda x: -len(x[1]))

# de-dup lists
for k in ('netcall_files',):
    report['check2_network'][k] = sorted(set(report['check2_network'][k]))
for k in ('scripts', 'eval_hits', 'b64_hits', 'runtime_download_hits'):
    report['check3_code'][k] = sorted(set(report['check3_code'][k]))
for k in ('sensitive_hits', 'home_refs'):
    report['check4_data'][k] = sorted(set(report['check4_data'][k]))
report['check5_update']['update_hits'] = sorted(set(report['check5_update']['update_hits']))

print(json.dumps(report, indent=2))
