"""Review Queue API endpoints — API Contract Section 4.6.

6 endpoints: list, get, approve, reject, regenerate, bulk-approve.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse, TaskResponse
from app.schemas.review import (
    ApproveRequest,
    BulkApproveRequest,
    BulkApproveResponse,
    RegenerateRequest,
    RejectRequest,
    ReviewQueueItem,
    ReviewQueueItemDetail,
)
from app.services import review_service

router = APIRouter(prefix="/review")


@router.get("/stats", response_model=DataResponse[dict])
async def get_review_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get review queue statistics."""
    from sqlalchemy import func, select

    from app.models.review_queue import ReviewQueue

    base = select(ReviewQueue.status, func.count(ReviewQueue.id)).where(
        ReviewQueue.user_id == current_user.id,
    ).group_by(ReviewQueue.status)
    result = await db.execute(base)
    by_status = {row[0]: row[1] for row in result.all()}

    type_base = select(ReviewQueue.item_type, func.count(ReviewQueue.id)).where(
        ReviewQueue.user_id == current_user.id,
        ReviewQueue.status == "pending",
    ).group_by(ReviewQueue.item_type)
    type_result = await db.execute(type_base)
    by_type = {row[0]: row[1] for row in type_result.all()}

    return {"data": {
        "pending": by_status.get("pending", 0),
        "approved": by_status.get("approved", 0),
        "rejected": by_status.get("rejected", 0),
        "total": sum(by_status.values()),
        "by_type": by_type,
    }}


@router.get("", response_model=PaginatedResponse[ReviewQueueItem])
async def list_review_items(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    type_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List review queue items with cursor pagination."""
    items, next_cursor, has_more = await review_service.list_review_items(
        db, current_user.id, cursor, limit, type_filter,
    )
    return {"data": items, "next_cursor": next_cursor, "has_more": has_more}


@router.get("/{item_id}", response_model=DataResponse[ReviewQueueItemDetail])
async def get_review_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a review queue item with full detail."""
    item = await review_service.get_review_item(db, current_user.id, item_id)
    if not item:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Review item not found")
    return {"data": item}


@router.post("/{item_id}/approve", response_model=DataResponse[ReviewQueueItem])
async def approve_item(
    item_id: uuid.UUID,
    body: ApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a review queue item, optionally with edited content."""
    item = await review_service.approve_item(db, current_user.id, item_id, body.edited_content)
    await db.commit()
    return {"data": item}


@router.post("/{item_id}/undo", response_model=DataResponse[ReviewQueueItem])
async def undo_approval(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Undo a review item approval within the 5-minute window."""
    item = await review_service.undo_approval(db, current_user.id, item_id)
    await db.commit()
    return {"data": item}


@router.post("/{item_id}/reject", response_model=DataResponse[ReviewQueueItem])
async def reject_item(
    item_id: uuid.UUID,
    body: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a review queue item with a reason."""
    item = await review_service.reject_item(db, current_user.id, item_id, body.reason)
    await db.commit()
    return {"data": item}


@router.post("/{item_id}/regenerate", response_model=TaskResponse)
async def regenerate_item(
    item_id: uuid.UUID,
    body: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Regenerate content for a review queue item."""
    task_id = await review_service.regenerate_item(db, current_user.id, item_id, body.instructions)
    await db.commit()
    return TaskResponse(task_id=task_id)


@router.post("/bulk-approve", response_model=BulkApproveResponse)
async def bulk_approve(
    body: BulkApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkApproveResponse:
    """Approve multiple review queue items at once."""
    count = await review_service.bulk_approve(db, current_user.id, body.item_ids)
    await db.commit()
    return BulkApproveResponse(approved=count)
