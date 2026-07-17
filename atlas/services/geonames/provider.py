import httpx

from core.config import settings
from core.logging import get_logger
from services.base import BaseProvider, ProviderResult

logger = get_logger()

GEONAMES_API = "http://api.geonames.org"


class GeoNamesProvider(BaseProvider):
    def __init__(self) -> None:
        self._username = settings.geonames_username
        if not self._username or self._username == "demo":
            logger.warning("geonames_username_not_configured")

    async def fetch(self, topic: str, entity_type: str, **kwargs) -> ProviderResult:
        data: dict = {
            "geoname_id": "",
            "name": topic,
            "latitude": None,
            "longitude": None,
            "country": "",
            "country_code": "",
            "population": None,
            "elevation": None,
            "timezone": "",
            "feature_code": "",
            "feature_class": "",
            "admin1": "",
            "admin2": "",
            "nearby_features": [],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                search_params = {
                    "q": topic,
                    "maxRows": "5",
                    "username": self._username,
                    "style": "FULL",
                    "formatted": "true",
                }
                search_resp = await client.get(
                    f"{GEONAMES_API}/searchJSON",
                    params=search_params,
                    headers={"User-Agent": "Atlas/1.0"},
                )
                if search_resp.status_code != 200:
                    return ProviderResult(source="geonames", data=data)

                search_data = search_resp.json()
                geonames = search_data.get("geonames", [])
                if not geonames:
                    return ProviderResult(source="geonames", data=data)

                best = geonames[0]
                data["geoname_id"] = str(best.get("geonameId", ""))
                data["name"] = best.get("name", topic)
                data["latitude"] = best.get("lat")
                data["longitude"] = best.get("lng")
                data["country"] = best.get("countryName", "")
                data["country_code"] = best.get("countryCode", "")
                data["population"] = best.get("population")
                data["elevation"] = best.get("elevation")
                data["timezone"] = best.get("timezone", {}).get("timeZoneId", "")
                data["feature_code"] = best.get("fcode", "")
                data["feature_class"] = best.get("fcl", "")
                data["admin1"] = best.get("adminName1", "")
                data["admin2"] = best.get("adminName2", "")

                nearby = await self._fetch_nearby(client, best.get("lat"), best.get("lng"))
                data["nearby_features"] = nearby

            except httpx.HTTPError as e:
                logger.error("geonames_request_failed", topic=topic, error=str(e))

        return ProviderResult(source="geonames", data=data)

    async def _fetch_nearby(
        self, client: httpx.AsyncClient, lat: float | None, lng: float | None
    ) -> list[dict]:
        if lat is None or lng is None:
            return []
        try:
            params = {
                "lat": str(lat),
                "lng": str(lng),
                "radius": "50",
                "maxRows": "20",
                "username": self._username,
                "style": "MEDIUM",
                "formatted": "true",
            }
            resp = await client.get(
                f"{GEONAMES_API}/findNearbyJSON",
                params=params,
                headers={"User-Agent": "Atlas/1.0"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                {
                    "geoname_id": str(n.get("geonameId", "")),
                    "name": n.get("name", ""),
                    "feature_code": n.get("fcode", ""),
                    "feature_class": n.get("fcl", ""),
                    "country": n.get("countryName", ""),
                    "distance_km": n.get("distance", "0"),
                }
                for n in data.get("geonames", [])
            ]
        except httpx.HTTPError:
            return []

    async def discover_topics(
        self, query: str, feature_code: str | None = None, max_rows: int = 50
    ) -> list[dict]:
        results: list[dict] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params: dict = {
                    "q": query,
                    "maxRows": str(max_rows),
                    "username": self._username,
                    "style": "MEDIUM",
                    "formatted": "true",
                }
                if feature_code:
                    params["fcode"] = feature_code

                resp = await client.get(
                    f"{GEONAMES_API}/searchJSON",
                    params=params,
                    headers={"User-Agent": "Atlas/1.0"},
                )
                if resp.status_code != 200:
                    return results

                data = resp.json()
                for geo in data.get("geonames", []):
                    feature = geo.get("fcode", "")
                    etype = self._map_feature_to_entity_type(feature)
                    results.append({
                        "name": geo.get("name", ""),
                        "entity_type": etype,
                        "country": geo.get("countryName", ""),
                        "geoname_id": str(geo.get("geonameId", "")),
                        "population": geo.get("population"),
                        "latitude": geo.get("lat"),
                        "longitude": geo.get("lng"),
                        "feature_code": feature,
                    })
            except httpx.HTTPError as e:
                logger.error("geonames_discover_failed", query=query, error=str(e))

        return results

    def _map_feature_to_entity_type(self, feature_code: str) -> str:
        mapping = {
            "PPL": "city",
            "PPLA": "city",
            "PPLC": "city",
            "PPLG": "city",
            "PPLA2": "town",
            "PPLA3": "town",
            "PPLA4": "village",
            "PPLF": "village",
            "ADM1": "state",
            "ADM2": "district",
            "ADM3": "district",
            "MT": "mountain",
            "MT_:": "mountain",
            "HLL": "hill",
            "PK": "peak",
            "VAL": "valley",
            "LK": "lake",
            "LKS": "lake",
            "LKH": "lake",
            "STM": "river",
            "STMI": "river",
            "FRST": "forest",
            "ISL": "island",
            "ISLS": "island",
            "PARK": "park",
            "RSV": "reservoir",
            "BAY": "bay",
            "GULF": "gulf",
            "SEA": "sea",
            "OCN": "ocean",
            "DES": "desert",
            "GL": "glacier",
            "CAPE": "cape",
            "PT": "point",
            "AMUS": "landmark",
            "MNMT": "landmark",
            "TMP": "temple",
            "CH": "church",
            "MUS": "museum",
            "FORT": "fort",
            "CAST": "castle",
            "RUIN": "ruins",
            "DAM": "dam",
            "BDG": "bridge",
            "TOWR": "tower",
            "LTHSE": "lighthouse",
            "AIRP": "airport",
            "STMX": "river",
        }
        return mapping.get(feature_code, "landmark")
