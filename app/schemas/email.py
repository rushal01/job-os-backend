"""Email intelligence schemas.

Referenced by file tree spec: app/schemas/email.py
"""

from pydantic import BaseModel


class EmailSettings(BaseModel):
    """Email integration settings."""

    gmail_connected: bool = False
    auto_scan: bool = False
    scan_frequency_minutes: int = 30


class EmailScanResult(BaseModel):
    """Result of an email scan operation."""

    emails_scanned: int
    matches_found: int
    status_updates: int
