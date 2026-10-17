"""Small on-disk response cache for slow external calls (LLM drafts, Bulbul audio, translations).

Purpose: a rehearsal run makes the identical stage run instant. Keys are content hashes of the full
request, so a changed transcript or prompt never gets a stale answer. Disable with VAANI_CACHE=off.
Nothing here is ever used as a substitute for a missing API key: the cache is only consulted by code
that would otherwise make the real call.
"""
import hashlib
import json
from pathlib import Path
from services import config


def enabled() -> bool:
    return config.CACHE_ENABLED


def key(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def _path(namespace: str, k: str) -> Path:
    return Path(config.DATA_DIR) / "cache" / namespace / (k + ".json")


def get(namespace: str, k: str):
    if not enabled():
        return None
    try:
        p = _path(namespace, k)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def put(namespace: str, k: str, value) -> None:
    if not enabled():
        return
    try:
        p = _path(namespace, k)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def clear() -> int:
    root = Path(config.DATA_DIR) / "cache"
    n = 0
    if root.exists():
        for f in root.rglob("*.json"):
            f.unlink(missing_ok=True)
            n += 1
    return n
