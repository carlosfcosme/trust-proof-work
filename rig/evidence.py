"""Evidence bundle builder (Audit Runner support).

Runs the REAL deterministic 5-check scanner (audit_skill.py, copied
byte-identical from the original Ep1 audit harness — sha256 in the corpus
manifest) over one skill directory and returns its JSON report. Also builds
a line index helper so verdict claims can cite file+line precisely.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCANNER = HERE / "audit_skill.py"


def scan_skill(skill_dir: Path, name: str) -> dict:
    out = subprocess.run(
        [sys.executable, str(SCANNER), str(skill_dir), name],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def find_line(skill_dir: Path, rel_file: str, needle: str):
    """Return (line_number, line_text) of the first line in rel_file
    containing needle, or None."""
    p = Path(skill_dir) / rel_file
    if not p.exists():
        return None
    for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
        if needle in line:
            return i, line.strip()
    return None


def find_line_re(skill_dir: Path, rel_file: str, pattern, flags=0):
    """Regex variant of find_line: first line matching pattern (a compiled
    pattern or a string), or None."""
    import re
    p = Path(skill_dir) / rel_file
    if not p.exists():
        return None
    rx = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
    for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
        if rx.search(line):
            return i, line.strip()
    return None


# The scanner's own base64 token pattern (audit_skill.py B64_RE) — kept in
# sync deliberately so citations resolve to the same blobs the scanner hit.
B64_TOKEN_RE = r"[A-Za-z0-9+/]{120,}={0,2}"


def find_b64_line(skill_dir: Path, rel_file: str, blob_len: int):
    """Cite the line carrying a base64 token of exactly blob_len chars —
    the precise blob a scanner b64_hit refers to (its hit string records
    the length and the decoded prefix, not the blob itself)."""
    import re
    p = Path(skill_dir) / rel_file
    if not p.exists():
        return None
    rx = re.compile(B64_TOKEN_RE)
    for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
        for m in rx.finditer(line):
            if len(m.group(0)) == blob_len:
                return i, line.strip()
    return None
