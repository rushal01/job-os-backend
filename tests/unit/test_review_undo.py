"""Tests for review queue undo approval via Redis TTL window."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError


class TestUndoApproval:
    """Test undo approval with Redis TTL window."""

    def _make_mock_db(self, item=None):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = item
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()
        return db

    def _make_review_item(self, status="approved"):
        item = MagicMock()
        item.id = uuid.uuid4()
        item.user_id = uuid.uuid4()
        item.status = status
        item.item_type = "resume"
        item.priority = 2
        item.created_at = datetime.utcnow()
        return item

    @pytest.mark.asyncio
    async def test_undo_within_window(self) -> None:
        from app.services.review_service import undo_approval

        item = self._make_review_item(status="approved")
        db = self._make_mock_db(item)

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        mock_redis.delete = AsyncMock()

        with patch("app.db.redis.get_redis", return_value=mock_redis):
            result = await undo_approval(db, item.user_id, item.id)

        assert result.status == "pending"
        mock_redis.delete.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_undo_after_window_expired(self) -> None:
        from app.services.review_service import undo_approval

        item = self._make_review_item(status="approved")
        db = self._make_mock_db(item)

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("app.db.redis.get_redis", return_value=mock_redis):
            with pytest.raises(AppError) as exc_info:
                await undo_approval(db, item.user_id, item.id)

        assert "expired" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_undo_not_approved_item(self) -> None:
        from app.services.review_service import undo_approval

        item = self._make_review_item(status="pending")
        db = self._make_mock_db(item)

        with pytest.raises(AppError) as exc_info:
            await undo_approval(db, item.user_id, item.id)

        assert "not approved" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_undo_not_found(self) -> None:
        from app.services.review_service import undo_approval

        db = self._make_mock_db(item=None)

        with pytest.raises(AppError):
            await undo_approval(db, uuid.uuid4(), uuid.uuid4())


class TestApproveCreatesUndoWindow:
    """Test that approving an item creates the Redis undo window."""

    @pytest.mark.asyncio
    async def test_approve_sets_redis_key(self) -> None:
        from app.services.review_service import approve_item

        item = MagicMock()
        item.id = uuid.uuid4()
        item.user_id = uuid.uuid4()
        item.status = "pending"

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = item
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch("app.db.redis.get_redis", return_value=mock_redis):
            result = await approve_item(db, item.user_id, item.id, None)

        assert result.status == "approved"
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300  # 5 minute TTL
