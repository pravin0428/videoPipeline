"""Phase 12 — Asset Memory: local library with embeddings and usage tracking.

Stores every downloaded asset in a SQLite database.
Before searching online, checks local assets first.
"""

import json
import sqlite3
import time
from pathlib import Path

from core.config import settings
from core.logging import get_logger

logger = get_logger()

ASSET_DB = Path(settings.app_data_dir) / "asset_memory.db"


class AssetMemory:
    def __init__(self):
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self):
        ASSET_DB.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(ASSET_DB))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                source TEXT,
                media_type TEXT,
                query TEXT,
                embedding TEXT,
                tags TEXT,
                usage_count INTEGER DEFAULT 0,
                scene_types TEXT,
                quality_score REAL DEFAULT 0.5,
                width INTEGER DEFAULT 1080,
                height INTEGER DEFAULT 1920,
                created_at REAL,
                last_used_at REAL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_media_type ON assets(media_type)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_usage ON assets(usage_count DESC)
        """)
        self._conn.commit()

    def store(self, file_path: str, source: str, media_type: str, query: str = "",
              tags: list[str] | None = None, quality_score: float = 0.5,
              width: int = 1080, height: int = 1920) -> bool:
        if not self._conn:
            return False
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO assets
                (file_path, source, media_type, query, tags, quality_score, width, height, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_path, source, media_type, query,
                json.dumps(tags or []), quality_score, width, height,
                time.time(), time.time(),
            ))
            self._conn.commit()
            return True
        except Exception as e:
            logger.debug("asset_memory_store_failed", error=str(e)[:60])
            return False

    def search(self, query: str, media_type: str | None = None,
               min_quality: float = 0.3, limit: int = 5) -> list[dict]:
        if not self._conn:
            return []

        lower = query.lower()
        tags_condition = " OR ".join(f"tags LIKE '%{t}%'" for t in lower.split()[:3])
        where = f"quality_score >= ? AND ({tags_condition})" if tags_condition else "quality_score >= ?"
        params: list = [min_quality]

        if media_type:
            where += " AND media_type = ?"
            params.append(media_type)

        try:
            rows = self._conn.execute(
                f"SELECT file_path, source, media_type, quality_score, usage_count, tags "
                f"FROM assets WHERE {where} ORDER BY quality_score DESC, usage_count DESC LIMIT ?",
                params + [limit],
            ).fetchall()
            return [
                {
                    "file_path": r[0], "source": r[1], "media_type": r[2],
                    "quality_score": r[3], "usage_count": r[4], "tags": r[5],
                }
                for r in rows
            ]
        except Exception as e:
            logger.debug("asset_memory_search_failed", error=str(e)[:60])
            return []

    def record_usage(self, file_path: str):
        if not self._conn:
            return
        try:
            self._conn.execute(
                "UPDATE assets SET usage_count = usage_count + 1, last_used_at = ? WHERE file_path = ?",
                (time.time(), file_path),
            )
            self._conn.commit()
        except Exception:
            pass

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
