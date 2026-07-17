import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.main import app
from core.database import get_db
from models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_atlas.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def mock_wikipedia_response() -> dict:
    return {
        "summary": "Test summary of the topic.",
        "extract": "Test extract of the topic with detailed information.",
        "page_url": "https://en.wikipedia.org/wiki/Test",
        "title": "Test",
    }


def mock_wikidata_response() -> dict:
    return {
        "entity_id": "Q42",
        "label": "Test",
        "description": "Test entity",
        "claims": {"P17": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q16"}}}}]},
        "coordinates": None,
        "official_name": "Test",
        "population": None,
        "country": "Q16",
    }


def mock_llm_response() -> dict:
    return {
        "summary": "Test is a landmark with significant historical importance.",
        "facts": [
            "Test has been a UNESCO World Heritage site since 1983.",
            "Test dates back to the 2nd century BCE.",
            "Test consists of 30 caves carved into rock.",
            "Test is located in Maharashtra, India.",
            "Test features both Buddhist and Hindu artwork.",
            "Test was rediscovered in 1819.",
        ],
    }
