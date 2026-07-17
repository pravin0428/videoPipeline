import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audio import Audio
from models.fact import Fact
from models.image import Image
from models.research_data import ResearchData
from models.script import Script
from models.topic import Topic
from models.video import Video


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, entity_type: str, country: str | None = None) -> Topic:
        topic = Topic(name=name, entity_type=entity_type, country=country, status="pending")
        self._session.add(topic)
        await self._session.flush()
        return topic

    async def get_by_id(self, topic_id: uuid.UUID) -> Topic | None:
        result = await self._session.execute(select(Topic).where(Topic.id == topic_id))
        return result.scalar_one_or_none()

    async def find_by_name(self, name: str) -> Topic | None:
        result = await self._session.execute(select(Topic).where(Topic.name == name))
        return result.scalar_one_or_none()

    async def update_status(self, topic_id: uuid.UUID, status: str) -> None:
        topic = await self.get_by_id(topic_id)
        if topic:
            topic.status = status
            await self._session.flush()


class ResearchDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, topic_id: uuid.UUID, summary: str | None, raw_data: dict | None) -> ResearchData:
        rd = ResearchData(topic_id=topic_id, summary=summary, raw_data=raw_data)
        self._session.add(rd)
        await self._session.flush()
        return rd

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> ResearchData | None:
        result = await self._session.execute(
            select(ResearchData).where(ResearchData.topic_id == topic_id)
        )
        return result.scalar_one_or_none()


class FactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, facts: list[Fact]) -> list[Fact]:
        self._session.add_all(facts)
        await self._session.flush()
        return facts

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> Sequence[Fact]:
        result = await self._session.execute(
            select(Fact).where(Fact.topic_id == topic_id).order_by(Fact.confidence_score.desc())
        )
        return result.scalars().all()


class ImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, images: list[Image]) -> list[Image]:
        self._session.add_all(images)
        await self._session.flush()
        return images

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> Sequence[Image]:
        result = await self._session.execute(
            select(Image).where(Image.topic_id == topic_id)
        )
        return result.scalars().all()


class ScriptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        topic_id: uuid.UUID,
        script_type: str,
        title: str,
        hook: str,
        script_text: str,
        estimated_duration: int,
        quality_score: float | None = None,
        raw_response: str | None = None,
        variant: str | None = None,
        readability_score: float | None = None,
        engagement_score: float | None = None,
        repetition_score: float | None = None,
        parent_script_id: uuid.UUID | None = None,
        hallucination_score: float | None = None,
        grounding_score: float | None = None,
        story_score: float | None = None,
        language_score: float | None = None,
        validation_passed: bool | None = None,
        validation_report: dict | None = None,
        generation_attempts: int | None = None,
        script_status: str | None = None,
    ) -> Script:
        script = Script(
            topic_id=topic_id,
            script_type=script_type,
            variant=variant,
            title=title,
            hook=hook,
            script_text=script_text,
            estimated_duration=estimated_duration,
            quality_score=quality_score,
            readability_score=readability_score,
            engagement_score=engagement_score,
            repetition_score=repetition_score,
            parent_script_id=parent_script_id,
            hallucination_score=hallucination_score,
            grounding_score=grounding_score,
            story_score=story_score,
            language_score=language_score,
            validation_passed=validation_passed,
            validation_report=validation_report,
            generation_attempts=generation_attempts,
            script_status=script_status,
            raw_response=raw_response,
        )
        self._session.add(script)
        await self._session.flush()
        return script

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> Script | None:
        result = await self._session.execute(
            select(Script).where(Script.topic_id == topic_id).order_by(Script.created_at.desc())
        )
        return result.scalars().first()

    async def get_all_by_topic_id(self, topic_id: uuid.UUID) -> Sequence[Script]:
        result = await self._session.execute(
            select(Script).where(Script.topic_id == topic_id).order_by(Script.created_at.desc())
        )
        return result.scalars().all()


class AudioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        topic_id: uuid.UUID,
        audio_path: str,
        duration_seconds: float,
        file_size: int,
        mime_type: str,
        voice: str,
        language: str = "hi-IN",
        script_id: uuid.UUID | None = None,
    ) -> Audio:
        audio = Audio(
            topic_id=topic_id,
            script_id=script_id,
            audio_path=audio_path,
            duration_seconds=duration_seconds,
            file_size=file_size,
            mime_type=mime_type,
            voice=voice,
            language=language,
        )
        self._session.add(audio)
        await self._session.flush()
        return audio

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> Audio | None:
        result = await self._session.execute(
            select(Audio).where(Audio.topic_id == topic_id).order_by(Audio.created_at.desc())
        )
        return result.scalars().first()


class VideoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        topic_id: uuid.UUID,
        video_path: str,
        duration_seconds: float,
        file_size: int,
        width: int = 1080,
        height: int = 1920,
        codec: str = "h264",
        mime_type: str = "video/mp4",
        image_count: int = 0,
        audio_id: uuid.UUID | None = None,
        subtitle_path: str | None = None,
        status: str = "completed",
    ) -> Video:
        video = Video(
            topic_id=topic_id,
            audio_id=audio_id,
            video_path=video_path,
            subtitle_path=subtitle_path,
            duration_seconds=duration_seconds,
            file_size=file_size,
            width=width,
            height=height,
            codec=codec,
            mime_type=mime_type,
            image_count=image_count,
            status=status,
        )
        self._session.add(video)
        await self._session.flush()
        return video

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> Video | None:
        result = await self._session.execute(
            select(Video).where(Video.topic_id == topic_id).order_by(Video.created_at.desc())
        )
        return result.scalars().first()
