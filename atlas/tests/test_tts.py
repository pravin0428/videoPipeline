from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from schemas.llm import LLMResponse
from services.base import ProviderResult
from services.tts.edge_provider import EdgeTTSProvider
from services.tts.provider import TTSResult
from tests.conftest import mock_llm_response, mock_wikidata_response, mock_wikipedia_response


def sample_hindi_script_text() -> str:
    return "अजंता की गुफाएं महाराष्ट्र में स्थित हैं। ये गुफाएं दूसरी शताब्दी ईसा पूर्व की हैं। यहां 30 गुफाएं हैं जो चट्टानों को काटकर बनाई गई हैं। यूनेस्को ने 1983 में इसे विश्व धरोहर घोषित किया।"


@pytest.mark.asyncio
async def test_tts_provider_estimate_duration() -> None:
    provider = EdgeTTSProvider()
    text = "एक दो तीन चार पांच"
    duration = provider._estimate_duration(text)
    assert duration >= 1.0
    assert isinstance(duration, float)


@pytest.mark.asyncio
async def test_tts_provider_synthesize_raises_if_edge_not_installed() -> None:
    provider = EdgeTTSProvider()

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("No such file")):
        with pytest.raises(RuntimeError, match="edge-tts is not installed"):
            await provider.synthesize("test text")


@pytest.mark.asyncio
async def test_tts_provider_synthesize_success() -> None:
    provider = EdgeTTSProvider(output_dir="/tmp/atlas_test_audio")

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        patch("builtins.open", unittest.mock.mock_open(read_data=b"fake-mp3-data")),
        patch("os.rename"),
    ):
        import builtins
        import unittest.mock
        result = await provider.synthesize("नमस्ते भारत")
        assert isinstance(result, TTSResult)
        assert len(result.audio_data) > 0
        assert result.mime_type == "audio/mp3"
        assert result.file_size > 0
        assert result.duration_seconds > 0
        assert result.stored_path != ""


@pytest.mark.asyncio
async def test_tts_api_no_script(client: AsyncClient) -> None:
    payload = {"name": "TTS No Script", "entity_type": "landmark", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.post(f"/api/topics/{topic_id}/tts")
    assert resp.status_code == 400
    assert "No script found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tts_api_not_found(client: AsyncClient) -> None:
    resp = await client.post("/api/topics/00000000-0000-0000-0000-000000000000/tts")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tts_api_get_nonexistent(client: AsyncClient) -> None:
    payload = {"name": "TTS Get Nonexistent", "entity_type": "city", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.get(f"/api/topics/{topic_id}/tts")
    assert resp.status_code == 404
    assert "No audio found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tts_api_generate_success_with_mocks(client: AsyncClient) -> None:
    payload = {"name": "TTS Generate Test", "entity_type": "landmark", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    wiki_result = ProviderResult(source="wikipedia", data=mock_wikipedia_response())
    wd_result = ProviderResult(source="wikidata", data=mock_wikidata_response())
    commons_result = ProviderResult(source="commons", data={"images": []})
    geonames_result = ProviderResult(source="geonames", data={})
    llm_data = mock_llm_response()
    llm_result = LLMResponse(summary=llm_data["summary"], facts=llm_data["facts"])

    with (
        patch("services.wikipedia.provider.WikipediaProvider.fetch", return_value=wiki_result),
        patch("services.wikidata.provider.WikidataProvider.fetch", return_value=wd_result),
        patch("services.commons.provider.CommonsProvider.fetch", return_value=commons_result),
        patch("services.geonames.provider.GeoNamesProvider.fetch", return_value=geonames_result),
        patch("services.llm.provider.LLMProvider.extract_knowledge", return_value=llm_result),
    ):
        await client.post(f"/api/topics/{topic_id}/research")

    from services.script.generator import ScriptGenerator

    with (
        patch.object(ScriptGenerator, "_query_ollama", return_value='{"title": "Test", "hook": "Hook", "script": "' + sample_hindi_script_text() + '", "estimated_duration_seconds": 50}'),
    ):
        script_resp = await client.post(f"/api/topics/{topic_id}/script")
        assert script_resp.status_code == 200

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        patch("builtins.open", unittest.mock.mock_open(read_data=b"fake-mp3-audio-data")),
        patch("os.rename"),
    ):
        import builtins
        import unittest.mock
        tts_resp = await client.post(f"/api/topics/{topic_id}/tts", json={"voice": "hi-IN-SwaraNeural"})
        assert tts_resp.status_code == 200
        data = tts_resp.json()
        assert "id" in data
        assert data["topic_id"] == topic_id
        assert data["mime_type"] == "audio/mp3"
        assert data["duration_seconds"] > 0


@pytest.mark.asyncio
async def test_tts_api_get_after_generate(client: AsyncClient) -> None:
    payload = {"name": "TTS Get After", "entity_type": "landmark", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    wiki_result = ProviderResult(source="wikipedia", data=mock_wikipedia_response())
    wd_result = ProviderResult(source="wikidata", data=mock_wikidata_response())
    commons_result = ProviderResult(source="commons", data={"images": []})
    geonames_result = ProviderResult(source="geonames", data={})
    llm_data = mock_llm_response()
    llm_result = LLMResponse(summary=llm_data["summary"], facts=llm_data["facts"])

    with (
        patch("services.wikipedia.provider.WikipediaProvider.fetch", return_value=wiki_result),
        patch("services.wikidata.provider.WikidataProvider.fetch", return_value=wd_result),
        patch("services.commons.provider.CommonsProvider.fetch", return_value=commons_result),
        patch("services.geonames.provider.GeoNamesProvider.fetch", return_value=geonames_result),
        patch("services.llm.provider.LLMProvider.extract_knowledge", return_value=llm_result),
    ):
        await client.post(f"/api/topics/{topic_id}/research")

    from services.script.generator import ScriptGenerator

    with (
        patch.object(ScriptGenerator, "_query_ollama", return_value='{"title": "TTS Get", "hook": "Hook", "script": "' + sample_hindi_script_text() + '", "estimated_duration_seconds": 45}'),
    ):
        await client.post(f"/api/topics/{topic_id}/script")

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        patch("builtins.open", unittest.mock.mock_open(read_data=b"fake-mp3-data")),
        patch("os.rename"),
    ):
        import builtins
        import unittest.mock
        await client.post(f"/api/topics/{topic_id}/tts")

    get_resp = await client.get(f"/api/topics/{topic_id}/tts")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["mime_type"] == "audio/mp3"
    assert data["voice"] == "hi-IN-SwaraNeural"
    assert data["language"] == "hi-IN"


@pytest.mark.asyncio
async def test_audio_model_create(db_session) -> None:
    from models.audio import Audio
    from models.topic import Topic

    topic = Topic(name="Audio Model Topic", entity_type="landmark")
    db_session.add(topic)
    await db_session.flush()

    audio = Audio(
        topic_id=topic.id,
        audio_path="/tmp/test_audio.mp3",
        duration_seconds=50.5,
        file_size=123456,
        mime_type="audio/mp3",
        voice="hi-IN-SwaraNeural",
        language="hi-IN",
    )
    db_session.add(audio)
    await db_session.commit()

    assert audio.id is not None
    assert audio.duration_seconds == 50.5
    assert audio.file_size == 123456
    assert audio.topic_id == topic.id
