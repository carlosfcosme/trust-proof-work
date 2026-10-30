"""Work layer: the content-studio workload adapter.

For the demo job this produces the 9 renditions the delivery credential
binds (3 languages x 3 aspects) as real MP4 files rendered locally with
ffmpeg, then QC-verifies them: count, container dimensions per aspect,
and SHA-256 recomputation. In the full product these renditions come
from the Viral Ecosystem Hunter pipeline and the covers from Muse
Image; the credential contract - outputs {format, language, aspect,
sha256} + QC object - is identical either way, and the transcript
labels which path produced a given run's files.
"""
import hashlib
import json
import subprocess
from pathlib import Path

LANGS = {
    "EN": ("Trust. Proof. Work.", "0x0B1220"),
    "ES": ("Confianza. Prueba. Trabajo.", "0x10200B"),
    "JA": ("Trust. Proof. Work. [JA]", "0x200B12"),
}
ASPECTS = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (720, 720)}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _render(out: Path, w: int, h: int, text: str, color: str):
    base = ["ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color}:s={w}x{h}:d=2:r=30"]
    enc = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           str(out)]
    if Path(FONT).exists():
        draw = (f"drawtext=fontfile={FONT}:text='{text}':fontcolor=white:"
                f"fontsize={max(28, w // 22)}:x=(w-text_w)/2:y=(h-text_h)/2")
        proc = subprocess.run(base + ["-vf", draw] + enc,
                              capture_output=True, text=True)
        if proc.returncode == 0:
            return
    # Fallback: language-tinted card without text (still a distinct,
    # correctly-sized rendition per language and aspect).
    proc = subprocess.run(base + enc, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {out}: {proc.stderr[-400:]}")


def _dims(p: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(p)],
        capture_output=True, text=True, check=True)
    s = json.loads(out.stdout)["streams"][0]
    return s["width"], s["height"]


def produce(job_id: str, out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for lang, (title, color) in LANGS.items():
        for aspect, (w, h) in ASPECTS.items():
            name = f"{job_id}_{lang}_{aspect.replace(':', 'x')}.mp4"
            p = out_dir / name
            _render(p, w, h, f"{title}  {lang} {aspect}", color)
            outputs.append({"format": "mp4", "language": lang,
                            "aspect": aspect, "sha256": _sha256(p),
                            "file": name})
    # QC: independent re-verification of every output.
    dims_ok = True
    hash_ok = True
    for o in outputs:
        p = out_dir / o["file"]
        w, h = ASPECTS[o["aspect"]]
        if _dims(p) != (w, h):
            dims_ok = False
        if _sha256(p) != o["sha256"]:
            hash_ok = False
    qc = {"count": len(outputs), "dimensions_ok": dims_ok,
          "hashes_ok": hash_ok,
          "distinct_hashes": len({o["sha256"] for o in outputs}) == len(outputs),
          "pass": len(outputs) == 9 and dims_ok and hash_ok
                  and len({o["sha256"] for o in outputs}) == len(outputs)}
    return {"outputs": outputs, "qc": qc, "out_dir": str(out_dir)}
