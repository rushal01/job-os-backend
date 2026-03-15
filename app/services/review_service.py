"""Review Queue service — approve, reject, regenerate review items.

Implements business logic for the human review queue per API Contract Section 4.6.
"""

import base64
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.review_queue import ReviewQueue


async def list_review_items(
    db: AsyncSession, user_id: uuid.UUID, cursor: str | None, limit: int, type_filter: str | None,
) -> tuple[list[ReviewQueue], str | None, bool]:
    """List review queue items with cursor pagination."""
    query = select(ReviewQueue).where(ReviewQueue.user_id == user_id)

    if type_filter:
        query = query.where(ReviewQueue.item_type == type_filter)

    # Decode cursor (base64-encoded offset)
    offset = 0
    if cursor:
        try:
            offset = int(base64.b64decode(cursor).decode())
        except Exception:
            offset = 0

    query = query.order_by(ReviewQueue.priority.asc(), ReviewQueue.created_at.desc())
    query = query.offset(offset).limit(limit + 1)

    result = await db.execute(query)
    items = list(result.scalars().all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if has_more:
        next_offset = offset + limit
        next_cursor = base64.b64encode(str(next_offset).encode()).decode()

    return items, next_cursor, has_more


async def get_review_item(db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID) -> ReviewQueue | None:
    """Get a review item by ID."""
    result = await db.execute(
        select(ReviewQueue).where(ReviewQueue.id == item_id, ReviewQueue.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def approve_item(
    db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID, edited_content: str | None,
) -> ReviewQueue:
    """Approve a review item, optionally with edited content."""
    result = await db.execute(
        select(ReviewQueue).where(ReviewQueue.id == item_id, ReviewQueue.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Review item not found")

    if item.status != "pending":
        raise AppError(code=ErrorCode.VALIDATION_ERROR, message=f"Item is already {item.status}")

    item.status = "approved"
    await db.flush()
    logger.info(f"Approved review item {item_id}")
    return item


async def reject_item(
    db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID, reason: str,
) -> ReviewQueue:
    """Reject a review item with a reason."""
    result = await db.execute(
        select(ReviewQueue).where(ReviewQueue.id == item_id, ReviewQueue.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Review item not found")

    if item.status != "pending":
        raise AppError(code=ErrorCode.VALIDATION_ERROR, message=f"Item is already {item.status}")

    item.status = "rejected"
    item.reject_reason = reason
    await db.flush()
    logger.info(f"Rejected review item {item_id}: {reason}")
    return item


async def regenerate_item(
    db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID, instructions: str,
) -> str:
    """Regenerate content for a review item. Returns task_id."""
    result = await db.execute(
        select(ReviewQueue).where(ReviewQueue.id == item_id, ReviewQueue.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Review item not found")

    from app.services.content_service import regenerate_document
    task_id = await regenerate_document(db, user_id, item.item_id, instructions)

    # Reset status to pending for re-review
    item.status = "pending"
    item.reject_reason = None
    await db.flush()

    logger.info(f"Regenerating review item {item_id}, task {task_id}")
    return task_id


async def bulk_approve(db: AsyncSession, user_id: uuid.UUID, item_ids: list[uuid.UUID]) -> int:
    """Approve multiple items at once. Returns count of approved items."""
    approved = 0
    for iid in item_ids:
        result = await db.execute(
            select(ReviewQueue).where(
                ReviewQueue.id == iid,
                ReviewQueue.user_id == user_id,
                ReviewQueue.status == "pending",
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.status = "approved"
            approved += 1

    await db.flush()
    logger.info(f"Bulk approved {approved} review items")
    return approved
