"""Files API endpoints — API Contract Section 4.7.

5 endpoints: presign-upload, confirm-upload, download-url, list, delete.
"""

import uuid

from fastapi import APIRouter, Depends, Query
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

router = APIRouter(prefix="/files")


@router.post("/presign-upload", response_model=PresignUploadResponse)
async def presign_upload(
    body: PresignUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PresignUploadResponse:
    """Generate a presigned URL for file upload to R2."""
    raise NotImplementedError


@router.post("/confirm-upload", response_model=DataResponse[dict])
async def confirm_upload(
    body: ConfirmUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Confirm a completed file upload and create a Document record."""
    raise NotImplementedError


@router.get("/{file_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DownloadUrlResponse:
    """Get a presigned download URL for a file."""
    raise NotImplementedError


@router.get("", response_model=DataResponse[list[dict]])
async def list_files(
    job_id: uuid.UUID | None = None,
    type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[dict]]:
    """List files filtered by job and/or type."""
    raise NotImplementedError


@router.delete("/{file_id}", response_model=SuccessResponse)
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Delete a file from R2 and remove the Document record."""
    raise NotImplementedError
