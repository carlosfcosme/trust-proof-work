"""Meta Model API adapter (api.meta.ai, OpenAI-compatible surface).

Used ONLY for advisory roles (interrogator drafting help, council seats)
when a key is configured. Deterministic layers never call this module,
and nothing in the verdict or settlement path depends on its output.

Key sources (first hit wins): env META_API_KEY, or the file named by env
TPW_META_KEY_FILE. Keys are never logged; the spend log records model id
and token usage only. Contributor-tier model ids (training-rights
discount) are refused by construction.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

BASE = "https://api.meta.ai/v1"


def _key() -> str | None:
    k = os.environ.get("META_API_KEY")
    if k:
        return k.strip()
    f = os.environ.get("TPW_META_KEY_FILE")
    if f and Path(f).exists():
        return Path(f).read_text().strip()
    # Project default: .secrets/ at the project root. Deliberately OUTSIDE
    # out/state - the demo resets its run state on every run and must never
    # be able to delete the key (it did, once, on 2026-10-30).
    default = Path(__file__).resolve().parent.parent / ".secrets" / "meta-api.key"
    if default.exists():
        return default.read_text().strip()
    return None


def available() -> bool:
    return _key() is not None


def _call(path: str, payload: dict | None = None) -> dict:
    key = _key()
    if key is None:
        raise RuntimeError("Meta API key not configured")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method="POST" if data else "GET",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def list_models() -> list[str]:
    out = _call("/models")
    return [m["id"] for m in out.get("data", []) if "id" in m]


def pick_spark_model() -> str | None:
    """First Standard-tier Spark id from the live inventory, or None.
    Contributor ids are refused even if they are the only Spark listed."""
    try:
        ids = list_models()
    except Exception:
        return None
    for mid in ids:
        if "spark" in mid.lower() and "contributor" not in mid.lower():
            return mid
    return None


def chat(model: str, messages: list[dict], spend_log: Path | None = None) -> str:
    if "contributor" in model.lower():
        raise RuntimeError("refused: contributor-tier model id")
    out = _call("/chat/completions",
                {"model": model, "messages": messages, "temperature": 0})
    if spend_log is not None:
        with open(spend_log, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "model": model,
                                "usage": out.get("usage", {})}) + "\n")
    return out["choices"][0]["message"]["content"]
