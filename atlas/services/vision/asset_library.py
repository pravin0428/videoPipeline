import json
import logging
import os
import time
import uuid
from pathlib import Path

import numpy as np

from core.config import settings

logger = logging.getLogger("atlas.vision.asset_library")

LIBRARY_PATH = Path(settings.app_data_dir) / "asset_library.json"
CACHE_DIR = Path(settings.app_data_dir) / "asset_cache"


class AssetLibrary:
    def __init__(self):
        self._entries: dict[str, dict] = {}
        self._dirty = False
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if LIBRARY_PATH.exists():
            try:
                data = json.loads(LIBRARY_PATH.read_text())
                self._entries = {e["url"]: e for e in data.get("assets", [])}
                logger.info("asset_library_loaded", count=len(self._entries))
            except Exception as e:
                logger.warning("asset_library_load_failed", error=str(e)[:80])
                self._entries = {}

    def _save(self):
        if not self._dirty:
            return
        try:
            data = {"assets": list(self._entries.values()), "version": 1}
            LIBRARY_PATH.write_text(json.dumps(data, indent=2))
            self._dirty = False
        except Exception as e:
            logger.warning("asset_library_save_failed", error=str(e)[:80])

    def get(self, url: str) -> dict | None:
        return self._entries.get(url)

    def has(self, url: str) -> bool:
        return url in self._entries

    def get_cached_path(self, url: str) -> str | None:
        entry = self._entries.get(url)
        if entry and entry.get("local_path") and os.path.isfile(entry["local_path"]):
            return entry["local_path"]
        return None

    def add(self, url: str, local_path: str, source: str, width: int = 0, height: int = 0,
            mime: str = "image/jpeg", quality_score: float = 50.0, embedding: bytes | None = None) -> str:
        if not local_path or not os.path.isfile(local_path):
            return ""

        cached_path = str(CACHE_DIR / f"al_{uuid.uuid4().hex[:12]}{Path(local_path).suffix}")
        try:
            data = Path(local_path).read_bytes()
            Path(cached_path).write_bytes(data)
        except Exception:
            return ""

        entry = {
            "url": url,
            "local_path": cached_path,
            "source": source,
            "width": width,
            "height": height,
            "mime": mime,
            "quality_score": quality_score,
            "times_used": 0,
            "last_used": None,
            "embedding": embedding.hex() if embedding else None,
            "created_at": time.time(),
        }
        self._entries[url] = entry
        self._dirty = True
        self._save()
        logger.debug("asset_library_added", url=url[:50], path=cached_path)
        return cached_path

    def record_use(self, url: str):
        entry = self._entries.get(url)
        if entry:
            entry["times_used"] = entry.get("times_used", 0) + 1
            entry["last_used"] = time.time()
            self._dirty = True

    def get_embedding(self, url: str) -> bytes | None:
        entry = self._entries.get(url)
        if entry and entry.get("embedding"):
            try:
                return bytes.fromhex(entry["embedding"])
            except Exception:
                return None
        return None

    def get_least_used(self, urls: list[str]) -> list[str]:
        scored = []
        for url in urls:
            entry = self._entries.get(url)
            if entry:
                scored.append((entry.get("times_used", 0), url))
            else:
                scored.append((0, url))
        scored.sort(key=lambda x: x[0])
        return [s[1] for s in scored]

    def get_stats(self) -> dict:
        total = len(self._entries)
        used = sum(1 for e in self._entries.values() if e.get("times_used", 0) > 0)
        total_uses = sum(e.get("times_used", 0) for e in self._entries.values())
        by_source: dict[str, int] = {}
        for e in self._entries.values():
            s = e.get("source", "unknown")
            by_source[s] = by_source.get(s, 0) + 1
        return {
            "total_assets": total,
            "used_assets": used,
            "total_uses": total_uses,
            "by_source": by_source,
        }

    def flush(self):
        self._save()

    @classmethod
    def get_cached_path_simple(cls, url: str) -> str | None:
        inst = cls._singleton if hasattr(cls, "_singleton") else None
        if inst is None:
            return None
        return inst.get_cached_path(url)


_asset_library: AssetLibrary | None = None


def get_asset_library() -> AssetLibrary:
    global _asset_library
    if _asset_library is None:
        _asset_library = AssetLibrary()
    return _asset_library
