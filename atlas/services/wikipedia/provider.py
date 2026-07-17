import httpx

from core.config import settings
from core.logging import get_logger
from services.base import BaseProvider, ProviderResult

logger = get_logger()

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
WIKIPEDIA_SEARCH = "https://en.wikipedia.org/w/api.php"


class WikipediaProvider(BaseProvider):
    async def fetch(self, topic: str, entity_type: str, **kwargs) -> ProviderResult:
        data: dict = {"summary": "", "extract": "", "page_url": "", "references": []}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    WIKIPEDIA_API.format(topic=topic.replace(" ", "_")),
                    headers={"User-Agent": "Atlas/1.0"},
                )
                if resp.status_code == 200:
                    page = resp.json()
                    data["summary"] = page.get("extract", "")
                    data["page_url"] = page.get("content_urls", {}).get("desktop", {}).get("page", "")
                    data["title"] = page.get("title", "")
                else:
                    data["summary"] = await self._search_then_fetch(topic, client)
            except httpx.HTTPError as e:
                logger.error("wikipedia_request_failed", topic=topic, error=str(e))

        return ProviderResult(source="wikipedia", data=data)

    async def _search_then_fetch(self, topic: str, client: httpx.AsyncClient) -> str:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json",
            "srlimit": 1,
        }
        try:
            search_resp = await client.get(WIKIPEDIA_SEARCH, params=params, headers={"User-Agent": "Atlas/1.0"})
            if search_resp.status_code != 200:
                return ""
            search_data = search_resp.json()
            pages = search_data.get("query", {}).get("search", [])
            if not pages:
                return ""
            title = pages[0]["title"]
            resp = await client.get(
                WIKIPEDIA_API.format(topic=title.replace(" ", "_")),
                headers={"User-Agent": "Atlas/1.0"},
            )
            if resp.status_code == 200:
                return resp.json().get("extract", "")
        except httpx.HTTPError:
            pass
        return ""
