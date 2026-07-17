import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from repositories.queue_repository import QueueRepository

logger = get_logger()


class QueueService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = QueueRepository(session)

    async def enqueue_topic(
        self,
        topic_id: uuid.UUID,
        source: str = "manual",
        priority: int = 0,
    ) -> dict:
        item = await self._repo.enqueue(
            topic_id=topic_id,
            source=source,
            priority=priority,
        )
        logger.info("topic_enqueued", topic_id=str(topic_id), queue_item_id=str(item.id))
        return {
            "queue_item_id": str(item.id),
            "topic_id": str(topic_id),
            "status": item.status,
            "source": source,
        }

    async def process_next(self) -> dict | None:
        item = await self._repo.dequeue()
        if not item:
            return None
        return {
            "queue_item_id": str(item.id),
            "topic_id": str(item.topic_id),
            "status": item.status,
        }

    async def mark_completed(self, item_id: uuid.UUID) -> None:
        await self._repo.mark_completed(item_id)

    async def mark_failed(self, item_id: uuid.UUID, error: str) -> None:
        await self._repo.mark_failed(item_id, error)

    async def get_queue_stats(self) -> dict:
        return {
            "pending": await self._repo.count_pending(),
            "processing": await self._repo.count_processing(),
            "failed": await self._repo.count_failed(),
            "total": (
                await self._repo.count_by_status("pending")
                + await self._repo.count_by_status("processing")
                + await self._repo.count_by_status("completed")
                + await self._repo.count_by_status("failed")
                + await self._repo.count_by_status("cancelled")
            ),
        }

    async def list_queue(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        items = await self._repo.list_by_status(status=status, limit=limit, offset=offset)
        return [
            {
                "id": str(item.id),
                "topic_id": str(item.topic_id),
                "status": item.status,
                "priority": item.priority,
                "retry_count": item.retry_count,
                "source": item.source,
                "error_message": item.error_message,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
