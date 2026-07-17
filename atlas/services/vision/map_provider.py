import io
import logging
import os
import re
import uuid
from pathlib import Path

import httpx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from core.config import settings

logger = logging.getLogger("atlas.vision.map")

MAP_CACHE_DIR = Path(settings.app_data_dir) / "map_cache"

COORD_PATTERN = re.compile(
    r"(-?\d+\.?\d*)\s*[°,]?\s*(-?\d+\.?\d*)"
)


class MapProvider:
    def __init__(self):
        MAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def generate_map(self, topic_name: str, research_data: dict | None = None) -> str | None:
        coords = self._extract_coordinates(research_data)
        if coords:
            return await self._generate_location_map(topic_name, *coords)

        if research_data:
            country = research_data.get("country") or self._extract_country(research_data)
            if country:
                return await self._generate_country_map(topic_name, country)

        return None

    def _extract_coordinates(self, research_data: dict | None) -> tuple[float, float] | None:
        if not research_data:
            return None
        raw = research_data.get("raw_data", {}) or {}
        wikidata = raw.get("wikidata", {}) or {}
        claims = wikidata.get("claims", {}) or {}

        coord_claims = claims.get("P625", [])
        if coord_claims:
            for claim in coord_claims:
                try:
                    value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                    lat = float(value.get("latitude", 0))
                    lon = float(value.get("longitude", 0))
                    if lat != 0 or lon != 0:
                        return (lat, lon)
                except (ValueError, TypeError):
                    pass

        wikipedia = raw.get("wikipedia", {}) or {}
        summary = wikipedia.get("summary", "") or ""
        coords_match = COORD_PATTERN.search(summary)
        if coords_match:
            try:
                lat = float(coords_match.group(1))
                lon = float(coords_match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass

        return None

    def _extract_country(self, research_data: dict) -> str | None:
        raw = research_data.get("raw_data", {}) or {}
        wikidata = raw.get("wikidata", {}) or {}
        country = wikidata.get("country", "")
        if country:
            return country
        wikipedia = raw.get("wikipedia", {}) or {}
        summary = wikipedia.get("summary", "") or ""
        country_match = re.search(r"(?:में|in|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", summary)
        if country_match:
            return country_match.group(1)
        return None

    async def _generate_location_map(self, topic_name: str, lat: float, lon: float) -> str | None:
        try:
            output_path = str(MAP_CACHE_DIR / f"map_{uuid.uuid4().hex[:8]}.png")

            fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100)
            fig.patch.set_facecolor("#0a1628")
            ax.set_facecolor("#0a1628")

            try:
                tile_img = await self._fetch_map_tile(lat, lon, zoom=5)
                if tile_img:
                    ax.imshow(tile_img, extent=[lon - 2, lon + 2, lat - 2, lat + 2], alpha=0.7)
            except Exception:
                pass

            ax.plot(lon, lat, marker="*", color="#ff4444", markersize=24,
                    markeredgecolor="white", markeredgewidth=2, zorder=5)
            ax.plot(lon, lat, marker="*", color="#ff6644", markersize=16,
                    markeredgecolor="white", markeredgewidth=1, zorder=6)

            ax.text(lon, lat - 0.15, topic_name, fontsize=14, color="white",
                    ha="center", va="top", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#000000aa", edgecolor="none"))

            ax.text(lon, lat + 0.15, f"{lat:.2f}°, {lon:.2f}°", fontsize=10,
                    color="#cccccc", ha="center", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#00000088", edgecolor="none"))

            ax.set_xlim(lon - 2, lon + 2)
            ax.set_ylim(lat - 2, lat + 2)
            ax.axis("off")

            fig.savefig(output_path, bbox_inches="tight", pad_inches=0,
                       facecolor=fig.get_facecolor(), dpi=100)
            plt.close(fig)

            if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
                logger.info("map_generated", topic=topic_name, lat=lat, lon=lon)
                return output_path

        except Exception as e:
            logger.warning("map_generation_failed", error=str(e)[:80])
            try:
                plt.close("all")
            except Exception:
                pass
        return None

    async def _generate_country_map(self, topic_name: str, country: str) -> str | None:
        try:
            output_path = str(MAP_CACHE_DIR / f"map_{uuid.uuid4().hex[:8]}.png")

            fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100)
            fig.patch.set_facecolor("#0a1628")
            ax.set_facecolor("#0a1628")

            ax.text(0.5, 0.6, topic_name, fontsize=22, color="white",
                    ha="center", va="center", fontweight="bold",
                    transform=ax.transAxes)
            ax.text(0.5, 0.45, country, fontsize=16, color="#aaaacc",
                    ha="center", va="center", transform=ax.transAxes)
            ax.text(0.5, 0.35, "📍", fontsize=48, ha="center", va="center",
                    transform=ax.transAxes)

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            fig.savefig(output_path, bbox_inches="tight", pad_inches=0,
                       facecolor=fig.get_facecolor(), dpi=100)
            plt.close(fig)

            if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
                logger.info("country_map_generated", topic=topic_name, country=country)
                return output_path
        except Exception as e:
            logger.warning("country_map_failed", error=str(e)[:80])
            try:
                plt.close("all")
            except Exception:
                pass
        return None

    @staticmethod
    async def _fetch_map_tile(lat: float, lon: float, zoom: int = 5) -> bytes | None:
        import math
        n = 2.0 ** zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)

        url = f"https://tile.openstreetmap.org/{zoom}/{x_tile}/{y_tile}.png"
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Atlas/1.0"})
                if resp.status_code == 200:
                    return resp.content
        except Exception:
            pass
        return None
