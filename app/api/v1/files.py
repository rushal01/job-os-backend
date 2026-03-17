"""Files API endpoints — API Contract Section 4.7.

5 endpoints: presign-upload, confirm-upload, download-url, list, delete.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.file import (
    ConfirmUploadRequest,
    DownloadUrlResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.services import file_service

router = APIRouter(prefix="/files")


@router.post("/presign-upload", response_model=PresignUploadResponse)
async def presign_upload(
    body: PresignUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a presigned URL for file upload to R2."""
    result = await file_service.presign_upload(
        current_user.id, body.filename, body.content_type, body.job_id
    )
    return result


@router.post("/confirm-upload", response_model=DataResponse[dict])
async def confirm_upload(
    body: ConfirmUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm a completed file upload and create a Document record."""
    doc = await file_service.confirm_upload(
        db, current_user.id, body.file_key, body.filename,
        body.size, body.content_type, body.job_id,
    )
    return {"data": {"id": str(doc.id), "filename": doc.filename, "file_size": doc.file_size}}


@router.get("/{file_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a presigned download URL for a file."""
    url = await file_service.get_download_url(db, current_user.id, file_id)
    return {"url": url}


@router.get("", response_model=DataResponse[list[dict]])
async def list_files(
    job_id: uuid.UUID | None = None,
    file_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List files filtered by job and/or type."""
    docs = await file_service.list_files(db, current_user.id, job_id, file_type)
    return {"data": [
        {
            "id": str(d.id),
            "filename": d.filename,
            "type": d.type,
            "content_type": d.content_type,
            "file_size": d.file_size,
            "job_id": str(d.job_id) if d.job_id else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]}


@router.delete("/{file_id}", response_model=SuccessResponse)
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a file from R2 and remove the Document record."""
    await file_service.delete_file(db, current_user.id, file_id)
    return {"success": True}
