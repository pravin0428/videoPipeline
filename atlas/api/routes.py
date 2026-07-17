import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from pipelines.discovery_pipeline import DiscoveryPipeline
from pipelines.research_pipeline import ResearchPipeline
from repositories.topic_repository import AudioRepository, FactRepository, ImageRepository, ResearchDataRepository, ScriptRepository, TopicRepository, VideoRepository
from schemas.audio import AudioResponse, TTSRequest, TTSGenerateResponse
from schemas.script import ScriptBatchGenerateResponse, ScriptGenerateRequest, ScriptGenerateResponse, ScriptReportResponse, ScriptResponse, ScriptVariantResponse
from schemas.video import VideoGenerateResponse, VideoResponse
from schemas.topic import (
    TopicCreate,
    TopicDetailResponse,
    TopicDiscoverRequest,
    TopicDiscoverResponse,
    TopicResponse,
)
from services.image_service import ImageService
from services.queue_service import QueueService
from services.quality.content_gate import validate_and_regenerate_variant
from services.script.generator import ScriptGenerator
from services.subtitle.generator import SubtitleGenerator
from services.tts.edge_provider import EdgeTTSProvider
from core.logging import get_logger

logger = get_logger()
router = APIRouter()


@router.post("/topics", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_topic(payload: TopicCreate, db: AsyncSession = Depends(get_db)) -> dict:
    repo = TopicRepository(db)
    topic = await repo.create(
        name=payload.name,
        entity_type=payload.entity_type,
        country=payload.country,
    )

    if not payload.skip_enqueue:
        qs = QueueService(db)
        await qs.enqueue_topic(topic_id=topic.id, source=payload.source, priority=payload.priority)

    return {"topic_id": str(topic.id)}


@router.post("/topics/{topic_id}/research", response_model=dict)
async def run_research(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    pipeline = ResearchPipeline(db)
    await pipeline.run(topic_id)
    return {"status": "completed"}


@router.get("/topics/{topic_id}", response_model=TopicDetailResponse)
async def get_topic_data(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    pipeline = ResearchPipeline(db)
    return await pipeline.get_topic_data(topic_id)


@router.get("/queue", response_model=dict)
async def list_queue(
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    qs = QueueService(db)
    items = await qs.list_queue(status=status_filter, limit=limit, offset=offset)
    stats = await qs.get_queue_stats()
    return {"items": items, "stats": stats}


@router.get("/queue/{item_id}", response_model=dict)
async def get_queue_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    from repositories.queue_repository import QueueRepository
    repo = QueueRepository(db)
    item = await repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {
        "id": str(item.id),
        "topic_id": str(item.topic_id),
        "status": item.status,
        "priority": item.priority,
        "retry_count": item.retry_count,
        "source": item.source,
        "error_message": item.error_message,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.post("/queue/process-next", response_model=dict)
async def process_next_queue_item(db: AsyncSession = Depends(get_db)) -> dict:
    qs = QueueService(db)
    item = await qs.process_next()
    if not item:
        return {"status": "empty", "message": "No pending items in queue"}

    try:
        pipeline = ResearchPipeline(db)
        topic_id = uuid.UUID(item["topic_id"])
        await pipeline.run(topic_id)
        await qs.mark_completed(uuid.UUID(item["queue_item_id"]))
        return {"status": "completed", "topic_id": item["topic_id"]}
    except Exception as e:
        await qs.mark_failed(uuid.UUID(item["queue_item_id"]), str(e))
        logger.error("queue_processing_failed", queue_item_id=item["queue_item_id"], error=str(e))
        return {"status": "failed", "error": str(e)}


@router.post("/discover", response_model=TopicDiscoverResponse)
async def discover_topics(payload: TopicDiscoverRequest, db: AsyncSession = Depends(get_db)) -> dict:
    dp = DiscoveryPipeline(db)
    return await dp.discover_and_enqueue(
        query=payload.query,
        entity_type=payload.entity_type,
        country_filter=payload.country_filter,
        max_results=payload.max_results,
    )


@router.get("/images/{topic_id}", response_model=list[dict])
async def list_topic_images(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[dict]:
    from repositories.topic_repository import ImageRepository
    repo = ImageRepository(db)
    images = await repo.get_by_topic_id(topic_id)
    return [
        {
            "id": str(img.id),
            "image_url": img.image_url,
            "source": img.source,
            "local_path": img.local_path,
            "file_size": img.file_size,
            "mime_type": img.mime_type,
            "author": img.author,
            "license": img.license,
        }
        for img in images
    ]


@router.post("/images/{topic_id}/download", response_model=dict)
async def download_topic_images(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    from repositories.topic_repository import ImageRepository
    repo = ImageRepository(db)
    images = await repo.get_by_topic_id(topic_id)
    if not images:
        return {"downloaded": 0, "message": "No images found for topic"}

    svc = ImageService()
    image_dicts = [{"url": img.image_url} for img in images]
    results = await svc.download_all(image_dicts, topic_id)

    for img, result in zip(images, results, strict=False):
        if result:
            img.local_path = result["file_path"]
            img.file_size = result["file_size"]
            img.mime_type = result["mime_type"]

    await db.flush()
    return {"downloaded": len(results), "total": len(images)}


@router.post("/topics/{topic_id}/script", response_model=ScriptBatchGenerateResponse)
async def generate_script(
    topic_id: uuid.UUID,
    payload: ScriptGenerateRequest = ScriptGenerateRequest(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    rd_repo = ResearchDataRepository(db)
    research_data = await rd_repo.get_by_topic_id(topic_id)

    fact_repo = FactRepository(db)
    facts = await fact_repo.get_by_topic_id(topic_id)

    if not facts:
        raise HTTPException(status_code=400, detail="No research facts available. Run research first.")

    fact_texts = [f.fact for f in facts[: payload.max_facts]]
    summary = research_data.summary if research_data else ""
    raw_data = research_data.raw_data if research_data else {}

    script_repo = ScriptRepository(db)
    parent_script: uuid.UUID | None = None
    variant_responses = []

    for variant_name in ["documentary", "mystery", "travel"]:
        v = await validate_and_regenerate_variant(
            facts=fact_texts,
            summary=summary,
            script_type=payload.script_type,
            variant_name=variant_name,
            topic_name=topic.name,
            country=topic.country,
            research_data=raw_data,
        )

        script = await script_repo.create(
            topic_id=topic_id,
            script_type=payload.script_type,
            variant=v.get("variant"),
            title=v["title"],
            hook=v["hook"],
            script_text=v["script"],
            estimated_duration=v["estimated_duration_seconds"],
            quality_score=v.get("quality_score"),
            readability_score=v.get("readability_score"),
            engagement_score=v.get("engagement_score"),
            repetition_score=v.get("repetition_score"),
            parent_script_id=parent_script,
            hallucination_score=v.get("hallucination_score"),
            grounding_score=v.get("grounding_score"),
            story_score=v.get("story_score"),
            language_score=v.get("language_score"),
            validation_passed=v.get("validation_passed"),
            validation_report=v.get("validation_report"),
            generation_attempts=v.get("generation_attempts"),
            script_status=v.get("script_status"),
        )
        if parent_script is None:
            parent_script = script.id

        variant_responses.append(ScriptVariantResponse(
            variant=v.get("variant", ""),
            title=v["title"],
            hook=v["hook"],
            script_text=v["script"],
            estimated_duration=v["estimated_duration_seconds"],
            quality_score=v.get("quality_score"),
            readability_score=v.get("readability_score"),
            engagement_score=v.get("engagement_score"),
            repetition_score=v.get("repetition_score"),
            hallucination_score=v.get("hallucination_score"),
            grounding_score=v.get("grounding_score"),
            story_score=v.get("story_score"),
            language_score=v.get("language_score"),
            validation_passed=v.get("validation_passed"),
            generation_attempts=v.get("generation_attempts"),
            script_status=v.get("script_status"),
        ))

    first = variant_responses[0] if variant_responses else {}
    return {
        "topic_id": topic_id,
        "script_type": payload.script_type,
        "variants": variant_responses,
    }


@router.get("/topics/{topic_id}/script", response_model=ScriptResponse | None)
async def get_script(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict | None:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    script_repo = ScriptRepository(db)
    script = await script_repo.get_by_topic_id(topic_id)
    if not script:
        raise HTTPException(status_code=404, detail="No script found for this topic. Generate one first.")

    return {
        "id": script.id,
        "topic_id": script.topic_id,
        "script_type": script.script_type,
        "variant": script.variant,
        "title": script.title,
        "hook": script.hook,
        "script_text": script.script_text,
        "estimated_duration": script.estimated_duration,
        "quality_score": script.quality_score,
        "readability_score": script.readability_score,
        "engagement_score": script.engagement_score,
        "repetition_score": script.repetition_score,
        "parent_script_id": script.parent_script_id,
        "created_at": script.created_at,
    }


@router.get("/topics/{topic_id}/script/report", response_model=ScriptReportResponse)
async def get_script_report(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    script_repo = ScriptRepository(db)
    scripts = await script_repo.get_all_by_topic_id(topic_id)
    if not scripts:
        raise HTTPException(status_code=404, detail="No scripts found for this topic.")

    primary = scripts[0]
    return {
        "id": primary.id,
        "topic_id": primary.topic_id,
        "script_type": primary.script_type,
        "variant": primary.variant,
        "title": primary.title,
        "hook": primary.hook,
        "script_text": primary.script_text,
        "estimated_duration": primary.estimated_duration,
        "quality_score": primary.quality_score,
        "readability_score": primary.readability_score,
        "engagement_score": primary.engagement_score,
        "repetition_score": primary.repetition_score,
        "hallucination_score": primary.hallucination_score,
        "grounding_score": primary.grounding_score,
        "story_score": primary.story_score,
        "language_score": primary.language_score,
        "validation_passed": primary.validation_passed,
        "validation_report": primary.validation_report,
        "generation_attempts": primary.generation_attempts,
        "script_status": primary.script_status,
        "created_at": primary.created_at,
    }


@router.post("/topics/{topic_id}/tts", response_model=TTSGenerateResponse)
async def generate_tts(
    topic_id: uuid.UUID,
    payload: TTSRequest = TTSRequest(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    script_repo = ScriptRepository(db)
    script = await script_repo.get_by_topic_id(topic_id)
    if not script:
        raise HTTPException(status_code=400, detail="No script found. Generate a script first.")

    provider = EdgeTTSProvider()
    try:
        result = await provider.synthesize(
            text=script.script_text,
            voice=payload.voice,
            rate=payload.rate,
            pitch=payload.pitch,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    audio_repo = AudioRepository(db)
    audio = await audio_repo.create(
        topic_id=topic_id,
        script_id=script.id,
        audio_path=result.stored_path,
        duration_seconds=result.duration_seconds,
        file_size=result.file_size,
        mime_type=result.mime_type,
        voice=payload.voice,
    )

    return {
        "id": audio.id,
        "topic_id": audio.topic_id,
        "script_id": audio.script_id,
        "audio_path": audio.audio_path,
        "duration_seconds": audio.duration_seconds,
        "file_size": audio.file_size,
        "mime_type": audio.mime_type,
        "voice": audio.voice,
    }


@router.get("/topics/{topic_id}/tts", response_model=AudioResponse | None)
async def get_tts(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict | None:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    audio_repo = AudioRepository(db)
    audio = await audio_repo.get_by_topic_id(topic_id)
    if not audio:
        raise HTTPException(status_code=404, detail="No audio found for this topic. Generate TTS first.")

    return {
        "id": audio.id,
        "topic_id": audio.topic_id,
        "script_id": audio.script_id,
        "audio_path": audio.audio_path,
        "duration_seconds": audio.duration_seconds,
        "file_size": audio.file_size,
        "mime_type": audio.mime_type,
        "voice": audio.voice,
        "language": audio.language,
        "created_at": audio.created_at,
    }


@router.post("/topics/{topic_id}/video", response_model=dict)
async def generate_video(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get the best script
    script_repo = ScriptRepository(db)
    script = await script_repo.get_by_topic_id(topic_id)
    if not script or not script.script_text:
        raise HTTPException(status_code=400, detail="No script found. Generate a script first.")

    # Get or generate TTS
    audio_repo = AudioRepository(db)
    audio = await audio_repo.get_by_topic_id(topic_id)
    if not audio or not os.path.isfile(audio.audio_path):
        from services.tts.edge_provider import EdgeTTSProvider
        tts_provider = EdgeTTSProvider()
        tts_result = await tts_provider.synthesize(text=script.script_text)
        audio = await audio_repo.create(
            topic_id=topic_id, script_id=script.id,
            audio_path=tts_result.stored_path,
            duration_seconds=tts_result.duration_seconds,
            file_size=tts_result.file_size,
            mime_type=tts_result.mime_type,
            voice=settings.tts_default_voice,
        )

    # Get research data for map generation and visual context
    rd_repo = ResearchDataRepository(db)
    research_data = await rd_repo.get_by_topic_id(topic_id)
    research_dict = {
        "raw_data": research_data.raw_data if research_data else {},
        "summary": research_data.summary if research_data else "",
        "country": topic.country,
    } if research_data else {"country": topic.country}

    # Run V3 pipeline
    generator = VideoShortGeneratorV3(topic_research_data=research_dict)
    try:
        result = await generator.generate(
            title=topic.name,
            script=script.script_text,
            output_filename=f"{topic_id}.mp4",
        )
    except Exception as e:
        logger.error("v3_generation_failed", topic_id=str(topic_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")

    video_path = result["video_path"]
    duration_seconds = result["duration"]
    quality = result.get("quality", {})

    video_repo = VideoRepository(db)
    video = await video_repo.create(
        topic_id=topic_id,
        audio_id=audio.id,
        video_path=video_path,
        subtitle_path=os.path.join(os.path.dirname(video_path), "subtitles.srt")
            if os.path.isfile(os.path.join(os.path.dirname(video_path), "subtitles.srt")) else None,
        duration_seconds=duration_seconds,
        file_size=os.path.getsize(video_path) if os.path.isfile(video_path) else 0,
        width=1080, height=1920,
        image_count=len(getattr(generator.provider, '_last_selection', [])),
        status="completed" if quality.get("passed") else "degraded",
    )

    return {
        "id": str(video.id),
        "topic_id": str(video.topic_id),
        "video_path": video.video_path,
        "duration_seconds": video.duration_seconds,
        "file_size": video.file_size,
        "width": video.width,
        "height": video.height,
        "status": video.status,
        "quality": quality,
    }


@router.get("/topics/{topic_id}/video", response_model=VideoResponse | None)
async def get_video(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict | None:
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    video_repo = VideoRepository(db)
    video = await video_repo.get_by_topic_id(topic_id)
    if not video:
        raise HTTPException(status_code=404, detail="No video found for this topic. Generate one first.")

    return {
        "id": video.id,
        "topic_id": video.topic_id,
        "audio_id": video.audio_id,
        "video_path": video.video_path,
        "subtitle_path": video.subtitle_path,
        "duration_seconds": video.duration_seconds,
        "file_size": video.file_size,
        "width": video.width,
        "height": video.height,
        "codec": video.codec,
        "mime_type": video.mime_type,
        "image_count": video.image_count,
        "status": video.status,
        "created_at": video.created_at,
    }
