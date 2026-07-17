import uuid
from collections.abc import Sequence
from typing import Any

import re

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.fact import Fact
from models.image import Image
from models.topic import Topic
from repositories.topic_repository import (
    FactRepository,
    ImageRepository,
    ResearchDataRepository,
    TopicRepository,
)
from schemas.llm import LLMResponse
from services.base import ProviderResult
from services.llm.provider import LLMProvider
from services.commons.provider import CommonsProvider
from services.geonames.provider import GeoNamesProvider
from services.wikipedia.provider import WikipediaProvider
from services.wikidata.provider import WikidataProvider

logger = get_logger()

CONFIDENCE_RULES: dict[str, float] = {
    "wikipedia": 25.0,
    "wikidata": 25.0,
    "commons": 20.0,
    "geonames": 15.0,
}

MIN_FACT_COUNT = 5


class ResearchPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._topic_repo = TopicRepository(session)
        self._research_data_repo = ResearchDataRepository(session)
        self._fact_repo = FactRepository(session)
        self._image_repo = ImageRepository(session)
        self._wikipedia = WikipediaProvider()
        self._wikidata = WikidataProvider()
        self._commons = CommonsProvider()
        self._geonames = GeoNamesProvider()
        self._llm = LLMProvider()

    async def run(self, topic_id: uuid.UUID) -> None:
        topic = await self._topic_repo.get_by_id(topic_id)
        if not topic:
            logger.error("topic_not_found", topic_id=str(topic_id))
            return

        await self._topic_repo.update_status(topic_id, "researching")

        try:
            wiki_result = await self._wikipedia.fetch(topic.name, topic.entity_type)
            wd_result = await self._wikidata.fetch(topic.name, topic.entity_type)
            commons_result = await self._commons.fetch(topic.name, topic.entity_type)
            geonames_result = await self._geonames.fetch(topic.name, topic.entity_type)

            merged: dict[str, dict] = {
                "wikipedia": wiki_result.data,
                "wikidata": wd_result.data,
                "commons": commons_result.data,
                "geonames": geonames_result.data,
            }

            llm_input = self._prepare_llm_input(merged)
            llm_response = await self._llm.extract_knowledge(llm_input)

            wiki_summary = (
                wiki_result.data.get("summary", "")
                if wiki_result.data
                else wd_result.data.get("description", "")
                if wd_result.data
                else ""
            )

            if len(llm_response.facts) < MIN_FACT_COUNT:
                fallback_facts = self._extract_facts_from_summary(wiki_summary)
                llm_response.facts.extend(fallback_facts)

            if len(llm_response.facts) < MIN_FACT_COUNT:
                raise RuntimeError(
                    f"Insufficient facts extracted ({len(llm_response.facts)}). "
                    f"At least {MIN_FACT_COUNT} facts required for topic: {topic.name}"
                )

            provider_results = [wiki_result, wd_result]
            if commons_result.data:
                provider_results.append(commons_result)
            if geonames_result.data:
                provider_results.append(geonames_result)

            await self._store_images(topic_id, commons_result.data)
            await self._research_data_repo.create(topic_id, wiki_summary, merged)
            await self._store_facts(topic_id, llm_response, provider_results)

            topic.country = wd_result.data.get("country", topic.country) if topic.country is None else topic.country

            await self._topic_repo.update_status(topic_id, "completed")
            logger.info("research_completed", topic_id=str(topic_id), topic_name=topic.name)

        except Exception as e:
            await self._topic_repo.update_status(topic_id, "failed")
            logger.error("research_failed", topic_id=str(topic_id), error=str(e))
            raise

    def _prepare_llm_input(self, merged: dict[str, dict]) -> dict[str, dict]:
        input_data = {}
        for source, data in merged.items():
            if not data:
                continue
            if source == "wikidata":
                cleaned = {k: v for k, v in data.items() if k != "claims"}
                if cleaned:
                    input_data[source] = cleaned
            else:
                input_data[source] = data
        return input_data

    def _extract_facts_from_summary(self, summary: str) -> list[str]:
        if not summary:
            return []

        sentences = re.split(r'[.!?।?!]+', summary)
        facts: list[str] = []
        seen: set[str] = set()

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence.split()) < 5:
                continue

            has_entity = bool(re.search(r'\b(स्थित|पाया|जाता|हैं|है|था|थी|था|गया|गई|गए|स्थापित|बनाया|निर्मित|खोज|मिला|मिली|पाई)', sentence))
            if not has_entity:
                continue

            normalized = sentence.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                facts.append(sentence)

            if len(facts) >= 10:
                break

        return facts

    async def _store_facts(
        self,
        topic_id: uuid.UUID,
        llm_response: LLMResponse,
        provider_results: list[ProviderResult],
    ) -> None:
        total_sources = len(provider_results)
        if total_sources == 0:
            return

        base_confidence = sum(
            CONFIDENCE_RULES.get(r.source, 0.0) for r in provider_results
        )
        base_confidence = min(base_confidence, 100.0)

        facts: list[Fact] = []
        for fact_text in llm_response.facts:
            if not fact_text.strip():
                continue
            fact = Fact(
                topic_id=topic_id,
                fact=fact_text.strip(),
                source=", ".join(r.source for r in provider_results),
                confidence_score=base_confidence,
            )
            facts.append(fact)

        if facts:
            await self._fact_repo.bulk_create(facts)
            logger.info("facts_stored", topic_id=str(topic_id), count=len(facts))

    async def _store_images(
        self,
        topic_id: uuid.UUID,
        commons_data: dict,
    ) -> None:
        images = commons_data.get("images", [])
        if not images:
            return

        image_models: list[Image] = []
        for img in images[:10]:
            image = Image(
                topic_id=topic_id,
                image_url=img.get("url", ""),
                source="commons",
                author=img.get("author"),
                license=img.get("license"),
            )
            image_models.append(image)

        if image_models:
            await self._image_repo.bulk_create(image_models)
            logger.info("images_stored", topic_id=str(topic_id), count=len(image_models))

    async def get_topic_data(self, topic_id: uuid.UUID) -> dict:
        research_data = await self._research_data_repo.get_by_topic_id(topic_id)
        facts: Sequence[Fact] = await self._fact_repo.get_by_topic_id(topic_id)
        images: Sequence[Image] = await self._image_repo.get_by_topic_id(topic_id)

        return {
            "summary": research_data.summary if research_data else None,
            "facts": [
                {"fact": f.fact, "source": f.source, "confidence_score": f.confidence_score}
                for f in facts
            ],
            "images": [
                {"image_url": img.image_url, "source": img.source}
                for img in images
            ],
        }
