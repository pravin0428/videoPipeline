import asyncio
import os
import random
import uuid
from pathlib import Path

import httpx

from core.config import settings
from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()


class StockVideoProvider(MediaProvider):
    media_type = "stock_video"

    def __init__(self):
        self.pexels_key = settings.pexels_api_key
        self._session: httpx.AsyncClient | None = None

    async def _client(self) -> httpx.AsyncClient:
        if self._session is None:
            self._session = httpx.AsyncClient(timeout=30.0)
        return self._session

    async def available(self) -> bool:
        return bool(self.pexels_key)

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        if not self.pexels_key:
            logger.warning("stock_video_no_key")
            return []

        queries = self._build_queries(plan)
        assets: list[MediaAsset] = []

        for q in queries:
            results = await self._search_pexels_videos(q)
            for video in results[:2]:
                download_path = str(output_dir / f"sv_{uuid.uuid4().hex[:8]}.mp4")
                ok = await self._download_video(video, download_path)
                if ok:
                    assets.append(MediaAsset(
                        media_type="stock_video",
                        file_path=download_path,
                        duration=min(video.get("duration", 6), plan.duration),
                        source="pexels_video",
                        metadata={"query": q, "width": video.get("width", 1080), "height": video.get("height", 1920)},
                    ))
                    if len(assets) >= 1:
                        break
            if assets:
                break

        return assets

    def _build_queries(self, plan: MediaPlan) -> list[str]:
        base = plan.narrative_context[:100]
        words = base.split()[:6]
        return [
            " ".join(words),
            plan.narrative_context.split("।")[0][:60],
            "nature documentary footage",
        ]

    async def _search_pexels_videos(self, query: str) -> list[dict]:
        client = await self._client()
        try:
            resp = await client.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={"query": query, "per_page": 5, "orientation": "portrait"},
            )
            if resp.status_code != 200:
                logger.debug("pexels_video_search_failed", status=resp.status_code, query=query)
                return []
            data = resp.json()
            videos = []
            for v in data.get("videos", []):
                video_files = v.get("video_files", [])
                best = self._best_file(video_files)
                if best:
                    videos.append({
                        "url": best["link"],
                        "width": best.get("width", 1080),
                        "height": best.get("height", 1920),
                        "duration": v.get("duration", 6),
                        "id": v.get("id"),
                    })
            return videos
        except Exception as e:
            logger.debug("pexels_video_search_error", error=str(e)[:80])
            return []

    @staticmethod
    def _best_file(files: list[dict]) -> dict | None:
        portrait = [f for f in files if f.get("width", 0) < f.get("height", 0) and f.get("width", 0) >= 720]
        if portrait:
            return portrait[0]
        landscape = [f for f in files if f.get("width", 0) >= 1280]
        if landscape:
            return landscape[0]
        return files[0] if files else None

    async def _download_video(self, video: dict, path: str) -> bool:
        url = video.get("url", "")
        if not url:
            return False
        try:
            client = await self._client()
            resp = await client.get(url, follow_redirects=True, timeout=httpx.Timeout(15.0, read=12.0))
            if resp.status_code == 200 and len(resp.content) > 1024:
                Path(path).write_bytes(resp.content)
                return True
        except Exception as e:
            logger.debug("stock_video_download_failed", error=str(e)[:80])
        return False

    async def close(self):
        if self._session:
            await self._session.aclose()
