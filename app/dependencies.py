"""Shared FastAPI dependencies.

Route-level dependencies are in app/api/deps.py.
This module provides application-wide dependencies.
"""

from app.db.redis import get_redis
from app.db.session import get_db

__all__ = ["get_db", "get_redis"]
