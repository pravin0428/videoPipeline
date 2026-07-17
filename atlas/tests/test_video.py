import os
import tempfile

import pytest
from httpx import AsyncClient

from services.subtitle.generator import SubtitleGenerator


@pytest.mark.asyncio
async def test_subtitle_generator_srt_format() -> None:
    gen = SubtitleGenerator()
    text = "अजंता की गुफाएं महाराष्ट्र में स्थित हैं। ये गुफाएं दूसरी शताब्दी ईसा पूर्व की हैं।"
    srt = gen.generate(text, 30.0)
    assert "1" in srt
    assert "-->" in srt
    assert "अजंता" in srt
    lines = srt.strip().split("\n")
    assert len(lines) >= 4


@pytest.mark.asyncio
async def test_subtitle_generator_empty_text() -> None:
    gen = SubtitleGenerator()
    srt = gen.generate("", 30.0)
    assert srt == ""


@pytest.mark.asyncio
async def test_subtitle_generator_timing() -> None:
    gen = SubtitleGenerator()
    text = "एक। दो। तीन। चार।"
    srt = gen.generate(text, 20.0)
    assert "00:00:00,000 -->" in srt
    assert srt.count("-->") == 4


@pytest.mark.asyncio
async def test_subtitle_split_into_cues() -> None:
    gen = SubtitleGenerator()
    text = "वाक्य एक। वाक्य दो। वाक्य तीन।"
    cues = gen._split_into_cues(text)
    assert len(cues) == 3
    assert "वाक्य एक" in cues[0]


@pytest.mark.asyncio
async def test_subtitle_format_time() -> None:
    gen = SubtitleGenerator()
    assert gen._format_time(0.0) == "00:00:00,000"
    assert gen._format_time(65.5) == "00:01:05,500"
    assert gen._format_time(3661.789) == "01:01:01,789"


@pytest.mark.asyncio
async def test_video_api_no_topic(client: AsyncClient) -> None:
    resp = await client.post("/api/topics/00000000-0000-0000-0000-000000000000/video")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_video_api_no_audio(client: AsyncClient) -> None:
    payload = {"name": "Video No Audio", "entity_type": "landmark", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.post(f"/api/topics/{topic_id}/video")
    assert resp.status_code == 400
    assert "No audio found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_video_api_no_images(client: AsyncClient, db_session) -> None:
    import uuid as uuid_mod
    from models.audio import Audio
    from models.topic import Topic

    topic = Topic(name="Video No Images", entity_type="landmark")
    db_session.add(topic)
    await db_session.flush()
    topic_id = str(topic.id)

    audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    audio_file.write(b"fake-mp3-data")
    audio_file.close()

    audio = Audio(
        topic_id=topic.id,
        audio_path=audio_file.name,
        duration_seconds=30.0,
        file_size=100,
        mime_type="audio/mpeg",
        voice="test",
        language="hi",
    )
    db_session.add(audio)
    await db_session.commit()

    resp = await client.post(f"/api/topics/{topic_id}/video")
    os.unlink(audio_file.name)
    assert resp.status_code == 400
    assert "no downloaded images" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_video_api_get_nonexistent(client: AsyncClient) -> None:
    payload = {"name": "Video Get None", "entity_type": "city", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.get(f"/api/topics/{topic_id}/video")
    assert resp.status_code == 404
    assert "no video found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_video_api_get_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/topics/00000000-0000-0000-0000-000000000000/video")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_video_model_create(db_session) -> None:
    from models.topic import Topic
    from models.video import Video

    topic = Topic(name="Video Model Test", entity_type="landmark")
    db_session.add(topic)
    await db_session.flush()

    video = Video(
        topic_id=topic.id,
        video_path="/tmp/test_video.mp4",
        duration_seconds=45.0,
        file_size=500000,
        width=1080,
        height=1920,
        codec="h264",
        mime_type="video/mp4",
        image_count=5,
        status="completed",
    )
    db_session.add(video)
    await db_session.commit()

    assert video.id is not None
    assert video.duration_seconds == 45.0
    assert video.file_size == 500000
    assert video.width == 1080
    assert video.height == 1920
    assert video.image_count == 5
