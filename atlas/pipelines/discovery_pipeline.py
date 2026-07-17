from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from repositories.queue_repository import QueueRepository
from repositories.topic_repository import TopicRepository
from services.geonames.provider import GeoNamesProvider

logger = get_logger()

ENTITY_TYPE_FEATURE_CODES: dict[str, str | None] = {
    "city": "PPL",
    "town": "PPLA4",
    "village": "PPLF",
    "mountain": "MT",
    "hill": "HLL",
    "lake": "LK",
    "river": "STM",
    "forest": "FRST",
    "island": "ISL",
}


class DiscoveryPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._topic_repo = TopicRepository(session)
        self._queue_repo = QueueRepository(session)
        self._geonames = GeoNamesProvider()

    async def discover_and_enqueue(
        self,
        query: str,
        entity_type: str | None = None,
        country_filter: str | None = None,
        max_results: int = 20,
    ) -> dict:
        feature_code = ENTITY_TYPE_FEATURE_CODES.get(entity_type) if entity_type else None

        discovered = await self._geonames.discover_topics(
            query=query,
            feature_code=feature_code,
            max_rows=max_results,
        )

        if country_filter:
            discovered = [d for d in discovered if d.get("country", "").lower() == country_filter.lower()]

        enqueued = 0
        skipped = 0
        for item in discovered:
            existing = await self._topic_repo.find_by_name(item["name"])
            if existing:
                skipped += 1
                continue

            topic = await self._topic_repo.create(
                name=item["name"],
                entity_type=item["entity_type"],
                country=item.get("country") or None,
            )
            await self._queue_repo.enqueue(
                topic_id=topic.id,
                source="geonames_discovery",
                priority=5,
            )
            enqueued += 1

        logger.info(
            "discovery_complete",
            query=query,
            found=len(discovered),
            enqueued=enqueued,
            skipped=skipped,
        )

        return {
            "query": query,
            "entity_type": entity_type,
            "total_found": len(discovered),
            "enqueued": enqueued,
            "skipped": skipped,
            "results": [
                {
                    "name": d["name"],
                    "entity_type": d["entity_type"],
                    "country": d.get("country", ""),
                    "geoname_id": d.get("geoname_id"),
                }
                for d in discovered
            ],
        }
