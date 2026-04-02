from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    data: list[T]
    next_cursor: str | None = None
    has_more: bool = False


class SuccessResponse(BaseModel):
    success: bool = True


class TaskResponse(BaseModel):
    task_id: str


class DataResponse(BaseModel, Generic[T]):  # noqa: UP046
    data: T
