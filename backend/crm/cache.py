"""Tiny JSON file cache for expensive per-customer / per-dashboard results.

The caller supplies a cheap data fingerprint (a hash of the deterministic
payload it just computed) so a cached entry is invalidated automatically
whenever the underlying DuckDB data changes. Entries live under
``<repo>/data/cache/<kind>/<key>.json`` as plain JSON for easy inspection.
Writes are atomic (write-to-temp + rename) so concurrent readers never see a
half-written file.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from backend.config import settings

_CACHE_ROOT = settings.repo_root / "data" / "cache"

# Bump when the cached payload/summary shape or its producing code changes, so
# stale entries from older versions are recomputed once after an update.
SCHEMA_VERSION = "5"


def _path(kind: str, key: str) -> Path:
    return _CACHE_ROOT / kind / f"{key}.json"


def fingerprint(payload: Any) -> str:
    """Stable short hash of a JSON-serializable payload (version-scoped)."""
    raw = json.dumps(
        {"v": SCHEMA_VERSION, "p": payload},
        ensure_ascii=False, sort_keys=True, default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load(kind: str, key: str) -> dict[str, Any] | None:
    """Return the cached entry (``{fingerprint, value}``) or None."""
    p = _path(kind, key)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(kind: str, key: str, value: Any, fp: str) -> None:
    """Atomically write ``{fingerprint: fp, value: value}``."""
    p = _path(kind, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprint": fp, "value": value}
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=str)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def cached(kind: str, key: str, compute: Callable[[], Any], fp: str) -> Any:
    """Return the cached value for (kind, key) when the stored fingerprint
    matches ``fp``; otherwise recompute with ``compute()`` and store it.
    """
    entry = load(kind, key)
    if entry is not None and entry.get("fingerprint") == fp:
        return entry["value"]
    value = compute()
    save(kind, key, value, fp)
    return value
