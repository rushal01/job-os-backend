"""File service — R2 presigned URLs, upload confirmation, document management.

Implements file operations per API Contract Section 4.7.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


async def presign_upload(user_id: uuid.UUID, filename: str, content_type: str, job_id: uuid.UUID | None) -> dict:
    """Generate a presigned upload URL for R2. Returns {upload_url, file_key}."""
    raise NotImplementedError


async def confirm_upload(db: AsyncSession, user_id: uuid.UUID, file_key: str, filename: str, size: int, content_type: str, job_id: uuid.UUID | None) -> Document:
    """Create a Document record after successful upload to R2."""
    raise NotImplementedError


async def get_download_url(db: AsyncSession, user_id: uuid.UUID, file_id: uuid.UUID) -> str:
    """Generate a presigned download URL for a file in R2."""
    raise NotImplementedError


async def list_files(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID | None, file_type: str | None) -> list[Document]:
    """List documents filtered by job and/or type."""
    raise NotImplementedError


async def delete_file(db: AsyncSession, user_id: uuid.UUID, file_id: uuid.UUID) -> None:
    """Delete a file from R2 and remove the Document record."""
    raise NotImplementedError
