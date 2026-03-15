"""File schemas — API Contract Section 4.7.

Defines request/response models for file upload, download, and management via R2.
"""

import uuid

from pydantic import BaseModel


class PresignUploadRequest(BaseModel):
    """POST /files/presign-upload request body."""

    filename: str
    content_type: str
    job_id: uuid.UUID | None = None


class PresignUploadResponse(BaseModel):
    """Response from POST /files/presign-upload."""

    upload_url: str
    file_key: str


class ConfirmUploadRequest(BaseModel):
    """POST /files/confirm-upload request body."""

    file_key: str
    filename: str
    size: int
    content_type: str
    job_id: uuid.UUID | None = None


class DownloadUrlResponse(BaseModel):
    """Response from GET /files/:id/download-url."""

    url: str
