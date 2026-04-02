"""File service — R2 presigned URLs, upload confirmation, document management.

Implements file operations per API Contract Section 4.7.
"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.document import Document


def _get_r2_client():
    """Try to create an R2 (S3-compatible) client. Returns None if not configured."""
    try:
        import boto3

        from app.config import settings

        if not settings.R2_ACCESS_KEY_ID or not settings.R2_ENDPOINT_URL:
            return None

        return boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    except Exception:
        return None


async def presign_upload(user_id: uuid.UUID, filename: str, content_type: str, job_id: uuid.UUID | None) -> dict:
    """Generate a presigned upload URL for R2. Returns {upload_url, file_key}."""
    file_key = f"uploads/{user_id}/{uuid.uuid4()}/{filename}"

    r2 = _get_r2_client()
    if r2 is not None:
        try:
            from app.config import settings

            upload_url = r2.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.R2_BUCKET_NAME,
                    "Key": file_key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,
            )
            logger.info("Generated R2 presigned upload URL for key {}", file_key)
            return {"upload_url": upload_url, "file_key": file_key}
        except Exception as e:
            logger.warning("R2 presign failed, falling back to local: {}", e)

    # Local fallback: return a local upload endpoint URL
    upload_url = f"/api/v1/files/local-upload/{file_key}"
    logger.info("Generated local upload URL for key {}", file_key)
    return {"upload_url": upload_url, "file_key": file_key}


async def confirm_upload(db: AsyncSession, user_id: uuid.UUID, file_key: str, filename: str, size: int, content_type: str, job_id: uuid.UUID | None) -> Document:
    """Create a Document record after successful upload to R2."""
    doc = Document(
        user_id=user_id,
        job_id=job_id,
        type="upload",
        filename=filename,
        r2_key=file_key,
        content_type=content_type,
        file_size=size,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    logger.info("Confirmed upload: doc {} for user {}", doc.id, user_id)
    return doc


async def get_download_url(db: AsyncSession, user_id: uuid.UUID, file_id: uuid.UUID) -> str:
    """Generate a presigned download URL for a file in R2."""
    result = await db.execute(
        select(Document).where(
            Document.id == file_id,
            Document.user_id == user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="File not found")

    r2 = _get_r2_client()
    if r2 is not None:
        try:
            from app.config import settings

            url = r2.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.R2_BUCKET_NAME,
                    "Key": doc.r2_key,
                },
                ExpiresIn=3600,
            )
            return url
        except Exception as e:
            logger.warning("R2 download presign failed, falling back to local: {}", e)

    # Local fallback
    return f"/api/v1/files/local-download/{doc.r2_key}"


async def list_files(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID | None, file_type: str | None) -> list[Document]:
    """List documents filtered by job and/or type."""
    query = select(Document).where(Document.user_id == user_id)

    if job_id is not None:
        query = query.where(Document.job_id == job_id)
    if file_type is not None:
        query = query.where(Document.type == file_type)

    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_file(db: AsyncSession, user_id: uuid.UUID, file_id: uuid.UUID) -> None:
    """Delete a file from R2 and remove the Document record."""
    result = await db.execute(
        select(Document).where(
            Document.id == file_id,
            Document.user_id == user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="File not found")

    # Try to delete from R2
    r2 = _get_r2_client()
    if r2 is not None:
        try:
            from app.config import settings

            r2.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=doc.r2_key)
            logger.info("Deleted file from R2: {}", doc.r2_key)
        except Exception as e:
            logger.warning("Failed to delete from R2 (continuing): {}", e)

    await db.delete(doc)
    await db.flush()
    logger.info("Deleted document {} for user {}", file_id, user_id)
