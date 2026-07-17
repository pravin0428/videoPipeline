import asyncio
import os
import uuid
from pathlib import Path

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger()

IMAGES_DIR = Path(settings.app_data_dir) / "images"


class ImageService:
    def __init__(self) -> None:
        self._download_dir = IMAGES_DIR
        self._download_dir.mkdir(parents=True, exist_ok=True)

    async def download_image(self, url: str, topic_id: uuid.UUID, index: int) -> dict | None:
        filename = f"{topic_id}_{index:04d}.jpg"
        filepath = self._download_dir / filename
        ext = self._guess_extension(url)
        if ext:
            filepath = filepath.with_suffix(ext)

        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Atlas/1.0"})
                if resp.status_code != 200:
                    logger.warning("image_download_failed", url=url, status=resp.status_code)
                    return None

                filepath.write_bytes(resp.content)
                logger.info(
                    "image_downloaded",
                    url=url[:80],
                    path=str(filepath),
                    size=len(resp.content),
                )
                return {
                    "file_path": str(filepath),
                    "file_name": filename,
                    "file_size": len(resp.content),
                    "mime_type": resp.headers.get("content-type", "image/jpeg"),
                }
        except httpx.HTTPError as e:
            logger.error("image_download_error", url=url, error=str(e))
            return None

    async def download_all(
        self, images: list[dict], topic_id: uuid.UUID
    ) -> list[dict]:
        tasks = []
        for i, img in enumerate(images):
            url = img.get("url") or img.get("thumb_url")
            if url:
                tasks.append(self.download_image(url, topic_id, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        downloaded: list[dict] = []
        for r in results:
            if isinstance(r, dict):
                downloaded.append(r)
        return downloaded

    def get_image_path(self, file_name: str) -> Path | None:
        filepath = self._download_dir / file_name
        if filepath.exists():
            return filepath
        return None

    def _guess_extension(self, url: str) -> str | None:
        url_lower = url.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".tiff"]:
            if ext in url_lower:
                return ext
        return ".jpg"
