from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from schemas.llm import LLMResponse
from services.base import ProviderResult
from services.script.generator import ScriptGenerator
from tests.conftest import mock_llm_response, mock_wikidata_response, mock_wikipedia_response


def sample_facts() -> list[str]:
    return [
        "अजंता की गुफाएं महाराष्ट्र में स्थित हैं।",
        "ये गुफाएं दूसरी शताब्दी ईसा पूर्व की हैं।",
        "यहां 30 गुफाएं हैं जो चट्टानों को काटकर बनाई गई हैं।",
        "यूनेस्को ने 1983 में इसे विश्व धरोहर घोषित किया।",
        "इनमें बौद्ध और हिंदू दोनों धर्मों की कलाकृति है।",
    ]


def sample_summary() -> str:
    return "अजंता की गुफाएं एक प्रसिद्ध ऐतिहासिक स्थल है."


def mock_script_response() -> dict:
    return {
        "title": "अजंता की गुफाएं - एक अद्भुत यात्रा",
        "hook": "क्या आप जानते हैं कि 2000 साल पहले बनी ये गुफाएं आज भी हैरान कर देती हैं?",
        "script": "अजंता की गुफाएं महाराष्ट्र में स्थित हैं। ये गुफाएं दूसरी शताब्दी ईसा पूर्व की हैं। यहां 30 गुफाएं हैं जो चट्टानों को काटकर बनाई गई हैं। यूनेस्को ने 1983 में इसे विश्व धरोहर घोषित किया। इनमें बौद्ध और हिंदू दोनों धर्मों की कलाकृति है। अगली बार जब आप महाराष्ट्र जाएं, तो इस चमत्कार को देखना न भूलें!",
        "estimated_duration_seconds": 50,
    }


DOCUMENTARY_RESPONSE = '{"title": "Doc Title", "hook": "Doc Hook", "script": "Documentary script body.", "estimated_duration_seconds": 50}'
MYSTERY_RESPONSE = '{"title": "Mystery Title", "hook": "Mystery Hook", "script": "Mystery script body.", "estimated_duration_seconds": 45}'
TRAVEL_RESPONSE = '{"title": "Travel Title", "hook": "Travel Hook", "script": "Travel script body.", "estimated_duration_seconds": 55}'


def mock_content_gate_variant(variant_name: str) -> dict:
    base = {
        "title": "Doc Title" if variant_name == "documentary" else "Mystery Title" if variant_name == "mystery" else "Travel Title",
        "hook": "Doc Hook" if variant_name == "documentary" else "Mystery Hook" if variant_name == "mystery" else "Travel Hook",
        "script": f"{variant_name.capitalize()} script body.",
        "estimated_duration_seconds": 50 if variant_name == "documentary" else 45 if variant_name == "mystery" else 55,
        "variant": variant_name,
        "quality_score": 85.0,
        "readability_score": 80.0,
        "engagement_score": 75.0,
        "repetition_score": 90.0,
        "hallucination_score": 10.0,
        "grounding_score": 90.0,
        "story_score": 85.0,
        "language_score": 95.0,
        "validation_passed": True,
        "validation_report": {
            "fact_grounding": {"is_valid": True, "confidence": 90.0, "hallucination_score": 10.0, "grounding_score": 90.0, "violations": [], "supported_claims": 3, "unsupported_claims": 0, "total_claims_checked": 3},
            "location_accuracy": {"is_valid": True, "confidence": 100.0, "violations": [], "locations_found": ["महाराष्ट्र"], "locations_validated": 1, "hallucinated_locations": []},
            "repetition_check": {"is_valid": True, "confidence": 100.0, "violations": [], "total_sentences": 5, "duplicate_pairs": 0, "max_similarity": 0.0},
            "language_check": {"is_valid": True, "confidence": 95.0, "violations": [], "hindi_ratio": 0.85, "total_chars": 100, "hindi_chars": 85, "english_chars": 5, "english_words_found": []},
            "story_structure": {"is_valid": True, "confidence": 85.0, "violations": [], "elements_found": {"hook": True, "context": True, "fact_section": True, "curiosity_ending": True}, "structure_score": 100.0},
        },
        "generation_attempts": 1,
        "script_status": "completed",
    }
    return base


@pytest.mark.asyncio
async def test_script_generator_build_prompt() -> None:
    generator = ScriptGenerator()
    facts = sample_facts()
    prompt = generator._build_prompt(facts, sample_summary(), "SHORTS_60", "documentary")
    assert "अजंता" in prompt
    assert "SHORTS_60" not in prompt or "60" in prompt
    assert len(prompt) > 100


@pytest.mark.asyncio
async def test_script_generator_parse_response() -> None:
    generator = ScriptGenerator()
    raw = '{"title": "Test", "hook": "Hook", "script": "Body", "estimated_duration_seconds": 45}'
    result = generator._parse_response(raw)
    assert result["title"] == "Test"
    assert result["hook"] == "Hook"
    assert result["script"] == "Body"
    assert result["estimated_duration_seconds"] == 45


@pytest.mark.asyncio
async def test_script_generator_parse_invalid() -> None:
    generator = ScriptGenerator()
    result = generator._parse_response("not json")
    assert result["title"] == "Parsing failed"
    assert result["estimated_duration_seconds"] == 0


@pytest.mark.asyncio
async def test_script_generator_quality_score_perfect() -> None:
    generator = ScriptGenerator()
    facts = sample_facts()
    script = mock_script_response()
    score = generator._score_quality(script, facts)
    assert 90.0 <= score <= 100.0


@pytest.mark.asyncio
async def test_script_generator_quality_score_empty() -> None:
    generator = ScriptGenerator()
    script = {"title": "", "hook": "", "script": "", "estimated_duration_seconds": 0}
    score = generator._score_quality(script, sample_facts())
    assert score <= 60.0


@pytest.mark.asyncio
async def test_script_generator_review_metrics() -> None:
    generator = ScriptGenerator()
    script = mock_script_response()
    facts = sample_facts()
    metrics = generator._compute_review_metrics(script, facts)
    assert "readability_score" in metrics
    assert "engagement_score" in metrics
    assert "repetition_score" in metrics
    assert 0 <= metrics["readability_score"] <= 100
    assert 0 <= metrics["engagement_score"] <= 100
    assert 0 <= metrics["repetition_score"] <= 100


@pytest.mark.asyncio
async def test_script_generator_generate_all() -> None:
    generator = ScriptGenerator()
    facts = sample_facts()
    with (
        patch.object(ScriptGenerator, "_query_ollama", side_effect=[
            DOCUMENTARY_RESPONSE,
            MYSTERY_RESPONSE,
            TRAVEL_RESPONSE,
        ]),
    ):
        variants = await generator.generate_all(facts, sample_summary())
        assert len(variants) == 3
        assert variants[0]["variant"] == "documentary"
        assert variants[1]["variant"] == "mystery"
        assert variants[2]["variant"] == "travel"


@pytest.mark.asyncio
async def test_script_api_generate_no_research(client: AsyncClient) -> None:
    payload = {"name": "Script No Research", "entity_type": "landmark", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.post(f"/api/topics/{topic_id}/script")
    assert resp.status_code == 400
    assert "research" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_script_api_generate_success(client: AsyncClient) -> None:
    payload = {"name": "Script Test Topic", "entity_type": "landmark", "skip_enqueue": True}
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
        research_resp = await client.post(f"/api/topics/{topic_id}/research")
        assert research_resp.status_code == 200

    from services.quality.content_gate import validate_and_regenerate_variant

    async def mock_validate(facts, summary, script_type, variant_name, topic_name, country, research_data):
        return mock_content_gate_variant(variant_name)

    with (
        patch("api.routes.validate_and_regenerate_variant", side_effect=mock_validate),
    ):
        script_resp = await client.post(f"/api/topics/{topic_id}/script")
        assert script_resp.status_code == 200
        data = script_resp.json()
        assert data["topic_id"] == topic_id
        assert len(data["variants"]) == 3
        doc = data["variants"][0]
        assert doc["title"] == "Doc Title"
        assert doc["hook"] == "Doc Hook"
        assert doc["script_text"] == "Documentary script body."
        assert doc["estimated_duration"] == 50
        assert doc["quality_score"] is not None


@pytest.mark.asyncio
async def test_script_api_get_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/topics/00000000-0000-0000-0000-000000000000/script")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_script_api_get_no_script(client: AsyncClient) -> None:
    payload = {"name": "Get No Script", "entity_type": "city", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.get(f"/api/topics/{topic_id}/script")
    assert resp.status_code == 404
    assert "no script" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_script_api_get_after_generate(client: AsyncClient) -> None:
    payload = {"name": "Get After Generate", "entity_type": "landmark", "skip_enqueue": True}
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

    from services.quality.content_gate import validate_and_regenerate_variant

    async def mock_validate(facts, summary, script_type, variant_name, topic_name, country, research_data):
        return mock_content_gate_variant(variant_name)

    with (
        patch("api.routes.validate_and_regenerate_variant", side_effect=mock_validate),
    ):
        gen_resp = await client.post(f"/api/topics/{topic_id}/script")
        assert gen_resp.status_code == 200

    get_resp = await client.get(f"/api/topics/{topic_id}/script")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["title"] == "Doc Title"
    assert data["hook"] == "Doc Hook"
    assert data["script_text"] == "Documentary script body."
    assert data["estimated_duration"] == 50
    assert data["quality_score"] is not None


@pytest.mark.asyncio
async def test_script_model_create(db_session) -> None:
    from models.script import Script
    from models.topic import Topic

    topic = Topic(name="Script Model Topic", entity_type="landmark")
    db_session.add(topic)
    await db_session.flush()

    script = Script(
        topic_id=topic.id,
        script_type="SHORTS_60",
        title="Test Title",
        hook="Test Hook",
        script_text="Test script body.",
        estimated_duration=50,
        quality_score=85.5,
        hallucination_score=10.0,
        grounding_score=90.0,
        story_score=85.0,
        language_score=95.0,
        validation_passed=True,
        generation_attempts=1,
        script_status="completed",
    )
    db_session.add(script)
    await db_session.commit()

    assert script.id is not None
    assert script.title == "Test Title"
    assert script.quality_score == 85.5
    assert script.hallucination_score == 10.0
    assert script.grounding_score == 90.0
    assert script.validation_passed is True
    assert script.script_status == "completed"
    assert script.topic_id == topic.id


@pytest.mark.asyncio
async def test_script_model_create_with_variant(db_session) -> None:
    from models.script import Script
    from models.topic import Topic

    topic = Topic(name="Variant Topic", entity_type="landmark")
    db_session.add(topic)
    await db_session.flush()

    script = Script(
        topic_id=topic.id,
        script_type="SHORTS_60",
        variant="documentary",
        title="Doc Title",
        hook="Doc Hook",
        script_text="Doc script body.",
        estimated_duration=50,
        quality_score=90.0,
        readability_score=85.0,
        engagement_score=92.0,
        repetition_score=95.0,
        hallucination_score=5.0,
        grounding_score=95.0,
        story_score=90.0,
        language_score=98.0,
        validation_passed=True,
        validation_report={"fact_grounding": {"is_valid": True}},
        generation_attempts=2,
        script_status="completed",
    )
    db_session.add(script)
    await db_session.flush()

    assert script.variant == "documentary"
    assert script.readability_score == 85.0
    assert script.engagement_score == 92.0
    assert script.repetition_score == 95.0
    assert script.hallucination_score == 5.0
    assert script.grounding_score == 95.0
    assert script.story_score == 90.0
    assert script.language_score == 98.0
    assert script.validation_passed is True
    assert script.validation_report == {"fact_grounding": {"is_valid": True}}
    assert script.generation_attempts == 2
    assert script.script_status == "completed"


@pytest.mark.asyncio
async def test_script_api_report_endpoint(client: AsyncClient) -> None:
    from services.quality.content_gate import validate_and_regenerate_variant

    payload = {"name": "Report Test", "entity_type": "landmark", "skip_enqueue": True}
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

    async def mock_validate(facts, summary, script_type, variant_name, topic_name, country, research_data):
        return mock_content_gate_variant(variant_name)

    with (
        patch("api.routes.validate_and_regenerate_variant", side_effect=mock_validate),
    ):
        await client.post(f"/api/topics/{topic_id}/script")

    report_resp = await client.get(f"/api/topics/{topic_id}/script/report")
    assert report_resp.status_code == 200
    data = report_resp.json()
    assert data["title"] == "Doc Title"
    assert data["hallucination_score"] == 10.0
    assert data["grounding_score"] == 90.0
    assert data["story_score"] == 85.0
    assert data["language_score"] == 95.0
    assert data["validation_passed"] is True
    assert data["validation_report"] is not None
    assert data["generation_attempts"] == 1
    assert data["script_status"] == "completed"


@pytest.mark.asyncio
async def test_script_api_report_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/topics/00000000-0000-0000-0000-000000000000/script/report")
    assert resp.status_code == 404
