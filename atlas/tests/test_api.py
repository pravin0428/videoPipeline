from unittest.mock import patch

import pytest
from httpx import AsyncClient

from schemas.llm import LLMResponse
from services.base import ProviderResult
from tests.conftest import mock_llm_response, mock_wikidata_response, mock_wikipedia_response


@pytest.mark.asyncio
async def test_create_topic(client: AsyncClient) -> None:
    payload = {"name": "Ajanta Caves", "entity_type": "landmark"}
    resp = await client.post("/api/topics", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "topic_id" in data
    assert isinstance(data["topic_id"], str)


@pytest.mark.asyncio
async def test_create_topic_with_country(client: AsyncClient) -> None:
    payload = {"name": "Taj Mahal", "entity_type": "landmark", "country": "India"}
    resp = await client.post("/api/topics", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "topic_id" in data


@pytest.mark.asyncio
async def test_create_topic_skip_enqueue(client: AsyncClient) -> None:
    payload = {"name": "Skip Enqueue", "entity_type": "city", "skip_enqueue": True}
    resp = await client.post("/api/topics", json=payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_get_topic_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/topics/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_research_not_found(client: AsyncClient) -> None:
    resp = await client.post("/api/topics/00000000-0000-0000-0000-000000000000/research")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_research_flow(client: AsyncClient) -> None:
    payload = {"name": "Ajanta Caves", "entity_type": "landmark", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    assert create_resp.status_code == 201
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
        assert research_resp.json()["status"] == "completed"

    get_resp = await client.get(f"/api/topics/{topic_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["summary"] == "Test summary of the topic."
    assert len(data["facts"]) == 6
    assert data["images"] == []


@pytest.mark.asyncio
async def test_queue_list_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "stats" in data


@pytest.mark.asyncio
async def test_queue_item_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/queue/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_queue_process_next_empty(client: AsyncClient) -> None:
    resp = await client.post("/api/queue/process-next")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "empty"


@pytest.mark.asyncio
async def test_discover_endpoint(client: AsyncClient) -> None:
    mock_geonames = [
        {"name": "K2", "entity_type": "mountain", "fcode": "MT", "country": "Pakistan", "countryName": "Pakistan", "geonameId": 1262259},
    ]

    with (
        patch("services.geonames.provider.GeoNamesProvider.discover_topics", return_value=mock_geonames),
    ):
        payload = {"query": "mountain", "entity_type": "mountain"}
        resp = await client.post("/api/discover", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 1
        assert data["enqueued"] == 1
        assert data["results"][0]["name"] == "K2"


@pytest.mark.asyncio
async def test_images_list_empty(client: AsyncClient) -> None:
    payload = {"name": "No Images Topic", "entity_type": "city", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.get(f"/api/images/{topic_id}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_images_download_no_images(client: AsyncClient) -> None:
    payload = {"name": "Download No Img", "entity_type": "city", "skip_enqueue": True}
    create_resp = await client.post("/api/topics", json=payload)
    topic_id = create_resp.json()["topic_id"]

    resp = await client.post(f"/api/images/{topic_id}/download")
    assert resp.status_code == 200
    data = resp.json()
    assert data["downloaded"] == 0
