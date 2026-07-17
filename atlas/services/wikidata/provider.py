import httpx

from core.logging import get_logger
from services.base import BaseProvider, ProviderResult

logger = get_logger()

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"


class WikidataProvider(BaseProvider):
    async def fetch(self, topic: str, entity_type: str, **kwargs) -> ProviderResult:
        data: dict = {
            "entity_id": "",
            "label": "",
            "description": "",
            "claims": {},
            "coordinates": None,
            "official_name": "",
            "population": None,
            "country": "",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                page_title = topic.replace(" ", "_")
                wiki_resp = await client.get(
                    WIKIPEDIA_SUMMARY.format(topic=page_title),
                    headers={"User-Agent": "Atlas/1.0"},
                )
                if wiki_resp.status_code != 200:
                    logger.warning("wikidata_no_wikipedia_page", topic=topic)
                    return ProviderResult(source="wikidata", data=data)

                wiki_page = wiki_resp.json()
                page_id = wiki_page.get("pageid")
                if not page_id:
                    return ProviderResult(source="wikidata", data=data)

                params = {
                    "action": "wbgetentities",
                    "sites": "enwiki",
                    "titles": wiki_page.get("title", topic),
                    "props": "claims|descriptions|labels",
                    "format": "json",
                }
                wd_resp = await client.get(WIKIDATA_API, params=params, headers={"User-Agent": "Atlas/1.0"})
                if wd_resp.status_code != 200:
                    return ProviderResult(source="wikidata", data=data)

                wd_data = wd_resp.json()
                entities = wd_data.get("entities", {})
                if not entities:
                    return ProviderResult(source="wikidata", data=data)

                entity_id = next(iter(entities))
                entity = entities[entity_id]

                data["entity_id"] = entity_id
                data["label"] = entity.get("labels", {}).get("en", {}).get("value", "")
                data["description"] = entity.get("descriptions", {}).get("en", {}).get("value", "")
                data["claims"] = self._extract_claims(entity.get("claims", {}))

                claims = entity.get("claims", {})
                data["coordinates"] = self._get_coordinate(claims)
                data["population"] = self._get_population(claims)
                data["country"] = self._get_country(claims)
                data["official_name"] = data["label"]

            except httpx.HTTPError as e:
                logger.error("wikidata_request_failed", topic=topic, error=str(e))

        return ProviderResult(source="wikidata", data=data)

    def _extract_claims(self, claims: dict) -> dict:
        result = {}
        for prop, claim_list in claims.items():
            values = []
            for claim in claim_list:
                mainsnak = claim.get("mainsnak", {})
                if mainsnak.get("snaktype") == "value":
                    datavalue = mainsnak.get("datavalue", {})
                    values.append(datavalue.get("value"))
            if values:
                result[prop] = values
        return result

    def _get_coordinate(self, claims: dict) -> dict | None:
        coord_claims = claims.get("P625", [])
        for claim in coord_claims:
            snak = claim.get("mainsnak", {})
            if snak.get("snaktype") == "value":
                val = snak.get("datavalue", {}).get("value", {})
                if isinstance(val, dict):
                    return {"latitude": val.get("latitude"), "longitude": val.get("longitude")}
        return None

    def _get_population(self, claims: dict) -> int | None:
        pop_claims = claims.get("P1082", [])
        for claim in pop_claims:
            snak = claim.get("mainsnak", {})
            if snak.get("snaktype") == "value":
                val = snak.get("datavalue", {}).get("value", {})
                if isinstance(val, dict):
                    try:
                        return int(val.get("amount", 0))
                    except (ValueError, TypeError):
                        pass
        return None

    def _get_country(self, claims: dict) -> str:
        country_claims = claims.get("P17", [])
        for claim in country_claims:
            snak = claim.get("mainsnak", {})
            if snak.get("snaktype") == "value":
                val = snak.get("datavalue", {}).get("value", {})
                if isinstance(val, dict):
                    return val.get("id", "")
        return ""
