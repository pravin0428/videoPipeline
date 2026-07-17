import pytest
from unittest.mock import AsyncMock, patch

from services.commons.provider import CommonsProvider
from services.geonames.provider import GeoNamesProvider
from services.wikipedia.provider import WikipediaProvider
from services.wikidata.provider import WikidataProvider
from services.llm.provider import LLMProvider


def _response(status: int, data: dict):
    class MockResponse:
        status_code = status

        def json(self):
            return data

        def raise_for_status(self):
            if status != 200:
                raise Exception(f"HTTP {status}")

    return MockResponse()


@pytest.mark.asyncio
async def test_wikipedia_provider_fetch_success() -> None:
    mock_get = AsyncMock(return_value=_response(200, {
        "extract": "Test extract",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Test"}},
        "title": "Test",
    }))

    with patch("httpx.AsyncClient.get", mock_get):
        provider = WikipediaProvider()
        result = await provider.fetch("Test", "landmark")
        assert result.source == "wikipedia"
        assert result.data["summary"] == "Test extract"


@pytest.mark.asyncio
async def test_wikipedia_provider_fetch_not_found() -> None:
    mock_get = AsyncMock(return_value=_response(404, {}))

    with patch("httpx.AsyncClient.get", mock_get):
        provider = WikipediaProvider()
        result = await provider.fetch("NonExistentTopicXYZ", "landmark")
        assert result.source == "wikipedia"
        assert isinstance(result.data, dict)


@pytest.mark.asyncio
async def test_wikidata_provider_fetch() -> None:
    mock_get = AsyncMock(side_effect=[
        _response(200, {"pageid": 12345, "title": "Test"}),
        _response(200, {
            "entities": {
                "Q42": {
                    "labels": {"en": {"value": "Test"}},
                    "descriptions": {"en": {"value": "Test entity"}},
                    "claims": {
                        "P625": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"latitude": 20.0, "longitude": 75.0}}}}],
                        "P1082": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"amount": "1000000"}}}}],
                        "P17": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q16"}}}}],
                    },
                }
            }
        }),
    ])

    with patch("httpx.AsyncClient.get", mock_get):
        provider = WikidataProvider()
        result = await provider.fetch("Test", "landmark")
        assert result.source == "wikidata"
        assert result.data["entity_id"] == "Q42"
        assert result.data["label"] == "Test"
        assert result.data["coordinates"] == {"latitude": 20.0, "longitude": 75.0}
        assert result.data["population"] == 1000000
        assert result.data["country"] == "Q16"


@pytest.mark.asyncio
async def test_commons_provider_fetch() -> None:
    mock_get = AsyncMock(side_effect=[
        _response(200, {
            "query": {
                "search": [
                    {"title": "File:Test_image.jpg"},
                    {"title": "File:Test_photo.png"},
                ]
            }
        }),
        _response(200, {
            "query": {
                "pages": {
                    "100": {
                        "title": "File:Test_image.jpg",
                        "imageinfo": [{"url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Test_image.jpg", "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Test_image.jpg"}],
                    },
                    "200": {
                        "title": "File:Test_photo.png",
                        "imageinfo": [{"url": "https://upload.wikimedia.org/wikipedia/commons/b/b2/Test_photo.png", "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Test_photo.png"}],
                    },
                }
            }
        }),
    ])

    with patch("httpx.AsyncClient.get", mock_get):
        provider = CommonsProvider()
        result = await provider.fetch("Test", "landmark")
        assert result.source == "commons"
        assert len(result.data.get("images", [])) == 2
        assert result.data["images"][0]["title"] == "Test_image.jpg"
        assert result.data["images"][1]["title"] == "Test_photo.png"


@pytest.mark.asyncio
async def test_commons_provider_fetch_by_category() -> None:
    mock_get = AsyncMock(return_value=_response(200, {
        "query": {
            "categorymembers": [
                {"title": "File:Test_image.jpg"},
            ]
        }
    }))

    with patch("httpx.AsyncClient.get", mock_get):
        provider = CommonsProvider()
        result = await provider.fetch_by_category("TestCategory", limit=5)
        assert len(result) == 1
        assert result[0]["title"] == "Test_image.jpg"


@pytest.mark.asyncio
async def test_geonames_provider_fetch() -> None:
    mock_get = AsyncMock(return_value=_response(200, {
        "geonames": [
            {
                "name": "Test Peak",
                "fcode": "MT",
                "countryName": "Testland",
                "geonameId": 12345,
                "lat": "10.0",
                "lng": "20.0",
                "elevation": 5000,
            }
        ],
        "totalResultsCount": 1,
    }))

    with patch("httpx.AsyncClient.get", mock_get):
        provider = GeoNamesProvider()
        result = await provider.fetch("Test", "mountain")
        assert result.source == "geonames"
        assert result.data["geoname_id"] == "12345"
        assert result.data["name"] == "Test Peak"
        assert result.data["country"] == "Testland"
        assert result.data["elevation"] == 5000


@pytest.mark.asyncio
async def test_geonames_discover_topics() -> None:
    mock_get = AsyncMock(return_value=_response(200, {
        "geonames": [
            {"name": "K2", "fcode": "MT", "countryName": "Pakistan", "geonameId": 1262259},
            {"name": "Nanga Parbat", "fcode": "MT", "countryName": "Pakistan", "geonameId": 1169397},
        ],
        "totalResultsCount": 2,
    }))

    with patch("httpx.AsyncClient.get", mock_get):
        provider = GeoNamesProvider()
        results = await provider.discover_topics(query="mountain", feature_code="MT", max_rows=10)
        assert len(results) == 2
        assert results[0]["name"] == "K2"
        assert results[0]["entity_type"] == "mountain"
        assert results[0]["country"] == "Pakistan"


@pytest.mark.asyncio
async def test_llm_provider_parse_response() -> None:
    provider = LLMProvider()
    raw_json = '{"summary": "Test summary.", "facts": ["Fact 1", "Fact 2"]}'
    result = provider._parse_response(raw_json)
    assert result.summary == "Test summary."
    assert result.facts == ["Fact 1", "Fact 2"]


@pytest.mark.asyncio
async def test_llm_provider_parse_invalid() -> None:
    provider = LLMProvider()
    result = provider._parse_response("not json")
    assert "Failed to parse" in result.summary
    assert result.facts == []


@pytest.mark.asyncio
async def test_llm_provider_build_prompt() -> None:
    provider = LLMProvider()
    content = {"wikipedia": {"summary": "Wiki summary"}, "wikidata": {"label": "Test"}, "commons": {"images": []}, "geonames": {"features": []}}
    prompt = provider._build_prompt(content)
    assert "WIKIPEDIA" in prompt
    assert "WIKIDATA" in prompt
    assert "Wiki summary" in prompt
    assert "Test" in prompt
