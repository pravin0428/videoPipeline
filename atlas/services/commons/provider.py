import httpx

from core.config import settings
from core.logging import get_logger
from services.base import BaseProvider, ProviderResult

logger = get_logger()

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


class CommonsProvider(BaseProvider):
    async def fetch(self, topic: str, entity_type: str, **kwargs) -> ProviderResult:
        data: dict = {
            "images": [],
            "total_results": 0,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": topic,
                    "srnamespace": "6",
                    "srlimit": "20",
                    "format": "json",
                    "srprop": "size|timestamp",
                }
                search_resp = await client.get(
                    COMMONS_API, params=params, headers={"User-Agent": "Atlas/1.0"}
                )
                if search_resp.status_code != 200:
                    return ProviderResult(source="commons", data=data)

                search_data = search_resp.json()
                results = search_data.get("query", {}).get("search", [])
                if not results:
                    return ProviderResult(source="commons", data=data)

                image_titles = [r["title"] for r in results if "File:" in r.get("title", "")]
                if not image_titles:
                    return ProviderResult(source="commons", data=data)

                img_params = {
                    "action": "query",
                    "titles": "|".join(image_titles[:10]),
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata|size|mime",
                    "format": "json",
                }
                img_resp = await client.get(
                    COMMONS_API, params=img_params, headers={"User-Agent": "Atlas/1.0"}
                )
                if img_resp.status_code != 200:
                    return ProviderResult(source="commons", data=data)

                img_data = img_resp.json()
                pages = img_data.get("query", {}).get("pages", {})
                for page_id, page in pages.items():
                    if page_id == "-1":
                        continue
                    title = page.get("title", "")
                    imageinfo = page.get("imageinfo", [])
                    if not imageinfo:
                        continue
                    info = imageinfo[0]
                    extmeta = info.get("extmetadata", {})
                    data["images"].append({
                        "title": title.replace("File:", "", 1),
                        "url": info.get("url", ""),
                        "thumb_url": info.get("thumburl", ""),
                        "description": extmeta.get("ImageDescription", {}).get("value", ""),
                        "author": extmeta.get("Artist", {}).get("value", ""),
                        "license": extmeta.get("LicenseShortName", {}).get("value", ""),
                        "mime": info.get("mime", ""),
                        "width": info.get("width", 0),
                        "height": info.get("height", 0),
                        "page_url": f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}",
                    })

                data["total_results"] = len(data["images"])

            except httpx.HTTPError as e:
                logger.error("commons_request_failed", topic=topic, error=str(e))

        return ProviderResult(source="commons", data=data)

    async def fetch_by_category(self, category: str, limit: int = 20) -> list[dict]:
        data: list[dict] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "action": "query",
                    "list": "categorymembers",
                    "cmtitle": f"Category:{category}",
                    "cmtype": "file",
                    "cmlimit": str(limit),
                    "format": "json",
                }
                resp = await client.get(
                    COMMONS_API, params=params, headers={"User-Agent": "Atlas/1.0"}
                )
                if resp.status_code != 200:
                    return data

                result = resp.json()
                for member in result.get("query", {}).get("categorymembers", []):
                    data.append({
                        "title": member.get("title", "").replace("File:", "", 1),
                        "page_id": member.get("pageid"),
                    })
            except httpx.HTTPError as e:
                logger.error("commons_category_failed", category=category, error=str(e))

        return data
