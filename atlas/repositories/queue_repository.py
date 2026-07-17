import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.topic_queue import TopicQueueItem


class QueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        topic_id: uuid.UUID,
        source: str = "manual",
        priority: int = 0,
        max_retries: int = 3,
    ) -> TopicQueueItem:
        item = TopicQueueItem(
            topic_id=topic_id,
            status="pending",
            priority=priority,
            max_retries=max_retries,
            source=source,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def dequeue(self) -> TopicQueueItem | None:
        result = await self._session.execute(
            select(TopicQueueItem)
            .where(TopicQueueItem.status == "pending")
            .order_by(TopicQueueItem.priority.desc(), TopicQueueItem.created_at.asc())
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if item:
            item.status = "processing"
            item.started_at = func.now()
            await self._session.flush()
        return item

    async def get_by_id(self, item_id: uuid.UUID) -> TopicQueueItem | None:
        result = await self._session.execute(
            select(TopicQueueItem).where(TopicQueueItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_by_topic_id(self, topic_id: uuid.UUID) -> Sequence[TopicQueueItem]:
        result = await self._session.execute(
            select(TopicQueueItem)
            .where(TopicQueueItem.topic_id == topic_id)
            .order_by(TopicQueueItem.created_at.desc())
        )
        return result.scalars().all()

    async def list_by_status(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[TopicQueueItem]:
        query = select(TopicQueueItem).order_by(TopicQueueItem.created_at.desc())
        if status:
            query = query.where(TopicQueueItem.status == status)
        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def mark_completed(self, item_id: uuid.UUID) -> None:
        item = await self.get_by_id(item_id)
        if item:
            item.status = "completed"
            item.completed_at = func.now()
            await self._session.flush()

    async def mark_failed(self, item_id: uuid.UUID, error_message: str) -> None:
        item = await self.get_by_id(item_id)
        if item:
            item.retry_count += 1
            if item.retry_count >= item.max_retries:
                item.status = "failed"
            else:
                item.status = "pending"
            item.error_message = error_message
            item.completed_at = func.now()
            await self._session.flush()

    async def mark_cancelled(self, item_id: uuid.UUID) -> None:
        item = await self.get_by_id(item_id)
        if item:
            item.status = "cancelled"
            item.completed_at = func.now()
            await self._session.flush()

    async def count_by_status(self, status: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(TopicQueueItem).where(TopicQueueItem.status == status)
        )
        return result.scalar() or 0

    async def count_pending(self) -> int:
        return await self.count_by_status("pending")

    async def count_processing(self) -> int:
        return await self.count_by_status("processing")

    async def count_failed(self) -> int:
        return await self.count_by_status("failed")
