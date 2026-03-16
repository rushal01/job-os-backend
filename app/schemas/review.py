"""Review Queue schemas — API Contract Section 4.6.

Defines request/response models for the human review queue.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ReviewQueueItem(BaseModel):
    """Summary item in the review queue list."""

    id: uuid.UUID
    user_id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    job_id: uuid.UUID | None = None
    priority: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewQueueItemDetail(BaseModel):
    """Detailed view of a review queue item with associated content."""

    id: uuid.UUID
    user_id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    job_id: uuid.UUID | None = None
    priority: int
    status: str
    reject_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveRequest(BaseModel):
    """POST /review/:id/approve request body."""

    edited_content: str | None = None


class RejectRequest(BaseModel):
    """POST /review/:id/reject request body."""

    reason: str


class RegenerateRequest(BaseModel):
    """POST /review/:id/regenerate request body."""

    instructions: str


class BulkApproveRequest(BaseModel):
    """POST /review/bulk-approve request body."""

    item_ids: list[uuid.UUID]


class BulkApproveResponse(BaseModel):
    """Response from POST /review/bulk-approve."""

    approved: int
