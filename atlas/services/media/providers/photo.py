import asyncio
import uuid
from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()


class PhotoProvider(MediaProvider):
    media_type = "photo"

    def __init__(self):
        self._pexels_key = ""
        self._pexels = None
        self._pixabay = None
        self._unsplash = None

    async def _lazy_init(self):
        if self._pexels is not None:
            return
        from pipelines.video_short_v3 import PexelsProvider, PixabayProvider, UnsplashProvider
        self._pexels = PexelsProvider()
        self._pixabay = PixabayProvider()
        self._unsplash = UnsplashProvider()

    async def available(self) -> bool:
        await self._lazy_init()
        return True

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        await self._lazy_init()

        queries = self._build_queries(plan)
        all_results = []

        for q in queries[:2]:
            results = await self._pexels.search(q, per_page=5)
            all_results.extend(results)
            results = await self._pixabay.search(q, per_page=5)
            all_results.extend(results)
            await asyncio.sleep(0.05)

        if not all_results:
            logger.info("photo_fallback_empty", scene=plan.scene_number)
            return []

        from pipelines.video_short_v3 import V3Asset
        assets: list[MediaAsset] = []
        for asset in all_results[:3]:
            local = await self._download_asset(asset, output_dir)
            if local:
                assets.append(MediaAsset(
                    media_type="photo",
                    file_path=local,
                    duration=plan.duration,
                    source=asset.source,
                    metadata={"url": asset.url, "width": asset.width, "height": asset.height},
                ))

        return assets

    @staticmethod
    def _build_queries(plan: MediaPlan) -> list[str]:
        base = plan.narrative_context[:80]
        return [base, "landscape nature photography documentary"]

    async def _download_asset(self, asset, output_dir: Path) -> str | None:
        if not asset.url:
            return None
        ext = ".jpg"
        if ".png" in asset.url.lower():
            ext = ".png"
        dest = str(output_dir / f"photo_{uuid.uuid4().hex[:8]}{ext}")

        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(asset.url)
                if resp.status_code == 200 and len(resp.content) > 1024:
                    Path(dest).write_bytes(resp.content)
                    return dest
        except Exception as e:
            logger.debug("photo_download_failed", error=str(e)[:60])
        return None
