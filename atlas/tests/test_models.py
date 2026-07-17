import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.fact import Fact
from models.image import Image
from models.research_data import ResearchData
from models.topic import Topic
from models.topic_queue import TopicQueueItem


@pytest.mark.asyncio
async def test_create_topic_model(db_session: AsyncSession) -> None:
    topic = Topic(name="Test Topic", entity_type="landmark", country="India", status="pending")
    db_session.add(topic)
    await db_session.commit()

    result = await db_session.execute(select(Topic).where(Topic.name == "Test Topic"))
    saved = result.scalar_one()
    assert saved.name == "Test Topic"
    assert saved.entity_type == "landmark"
    assert saved.country == "India"
    assert saved.status == "pending"
    assert saved.id is not None


@pytest.mark.asyncio
async def test_topic_relationships(db_session: AsyncSession) -> None:
    topic = Topic(name="Related Topic", entity_type="city")
    db_session.add(topic)
    await db_session.flush()

    rd = ResearchData(topic_id=topic.id, summary="Summary text", raw_data={"key": "value"})
    fact = Fact(topic_id=topic.id, fact="Some fact", source="wikipedia", confidence_score=50.0)
    img = Image(
        topic_id=topic.id,
        image_url="https://example.com/img.jpg",
        source="commons",
        local_path="/tmp/img.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        author="Test Author",
        license="CC-BY",
    )
    db_session.add_all([rd, fact, img])
    await db_session.commit()

    result = await db_session.execute(
        select(Topic)
        .where(Topic.id == topic.id)
        .options(selectinload(Topic.research_data), selectinload(Topic.facts), selectinload(Topic.images))
    )
    saved = result.scalar_one()
    assert len(saved.research_data) == 1
    assert len(saved.facts) == 1
    assert len(saved.images) == 1
    assert saved.images[0].local_path == "/tmp/img.jpg"
    assert saved.images[0].file_size == 1024
    assert saved.images[0].author == "Test Author"


@pytest.mark.asyncio
async def test_fact_confidence_scoring(db_session: AsyncSession) -> None:
    topic = Topic(name="Score Test", entity_type="landmark")
    db_session.add(topic)
    await db_session.flush()

    high = Fact(topic_id=topic.id, fact="High confidence fact", source="wikipedia", confidence_score=100.0)
    low = Fact(topic_id=topic.id, fact="Low confidence fact", source="overpass", confidence_score=15.0)
    db_session.add_all([high, low])
    await db_session.commit()

    result = await db_session.execute(
        select(Fact).where(Fact.topic_id == topic.id).order_by(Fact.confidence_score.desc())
    )
    facts = result.scalars().all()
    assert facts[0].confidence_score == 100.0
    assert facts[1].confidence_score == 15.0


@pytest.mark.asyncio
async def test_research_data_raw_data(db_session: AsyncSession) -> None:
    topic = Topic(name="Raw Topic", entity_type="lake")
    db_session.add(topic)
    await db_session.flush()

    raw = {"wikipedia": {"summary": "test"}, "wikidata": {"id": "Q1"}}
    rd = ResearchData(topic_id=topic.id, summary="test", raw_data=raw)
    db_session.add(rd)
    await db_session.commit()

    result = await db_session.execute(select(ResearchData).where(ResearchData.topic_id == topic.id))
    saved = result.scalar_one()
    assert saved.raw_data == raw


@pytest.mark.asyncio
async def test_topic_queue_item_create(db_session: AsyncSession) -> None:
    topic = Topic(name="Queue Topic", entity_type="mountain")
    db_session.add(topic)
    await db_session.flush()

    qitem = TopicQueueItem(
        topic_id=topic.id,
        status="pending",
        priority=10,
        source="test",
    )
    db_session.add(qitem)
    await db_session.commit()

    result = await db_session.execute(
        select(TopicQueueItem).where(TopicQueueItem.topic_id == topic.id)
    )
    saved = result.scalar_one()
    assert saved.status == "pending"
    assert saved.priority == 10
    assert saved.source == "test"
    assert saved.retry_count == 0


@pytest.mark.asyncio
async def test_topic_queue_item_status_transitions(db_session: AsyncSession) -> None:
    topic = Topic(name="Queue Status", entity_type="city")
    db_session.add(topic)
    await db_session.flush()

    qitem = TopicQueueItem(topic_id=topic.id)
    db_session.add(qitem)
    await db_session.flush()
    assert qitem.status == "pending"

    qitem.status = "processing"
    await db_session.flush()
    assert qitem.status == "processing"

    qitem.status = "completed"
    await db_session.flush()
    assert qitem.status == "completed"


@pytest.mark.asyncio
async def test_topic_queue_item_max_retries(db_session: AsyncSession) -> None:
    topic = Topic(name="Queue Retry", entity_type="village")
    db_session.add(topic)
    await db_session.flush()

    qitem = TopicQueueItem(topic_id=topic.id, max_retries=2)
    db_session.add(qitem)
    await db_session.flush()

    qitem.retry_count = 1
    qitem.status = "pending"
    qitem.error_message = "Attempt 1 failed"
    await db_session.flush()

    qitem.retry_count = 2
    qitem.status = "failed"
    await db_session.flush()

    result = await db_session.execute(select(TopicQueueItem).where(TopicQueueItem.id == qitem.id))
    saved = result.scalar_one()
    assert saved.status == "failed"
    assert saved.retry_count == 2
