"""Schema barrel exports — all Pydantic models used by API routes."""

from app.schemas.admin import (
    AdminUser,
    AdminUserDetail,
    FeatureFlags,
    FeatureFlagUpdate,
    RoleUpdate,
    SuspendRequest,
    SystemHealth,
)
from app.schemas.ai import (
    AIRequest,
    AIResponse,
    APIKeyCreate,
    APIKeyInfo,
    APIKeyValidation,
    ModelConfig,
    ModelConfigUpdate,
    ProviderConfig,
    UsageStats,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    SessionResponse,
    SessionSchema,
    SignupRequest,
    UserResponse,
    UserSchema,
)
from app.schemas.common import (
    DataResponse,
    ErrorBody,
    ErrorDetail,
    ErrorEnvelope,
    PaginatedResponse,
    SuccessResponse,
    TaskResponse,
)
from app.schemas.copilot import ChatRequest, CopilotMessage
from app.schemas.education import EducationCreate, EducationResponse, EducationUpdate
from app.schemas.email import EmailScanResult, EmailSettings
from app.schemas.file import (
    ConfirmUploadRequest,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.schemas.interview import InterviewCreate, InterviewResponse, InterviewUpdate
from app.schemas.job import (
    BulkScoreRequest,
    DiscoverRequest,
    JobCreate,
    JobFilters,
    JobResponse,
    JobStatusUpdate,
    ScoreBreakdown,
)
from app.schemas.notification import NotificationResponse
from app.schemas.profile import (
    CloneRequest,
    ProfileCompleteness,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.review import (
    ApproveRequest,
    BulkApproveRequest,
    BulkApproveResponse,
    RegenerateRequest,
    RejectRequest,
    ReviewQueueItem,
    ReviewQueueItemDetail,
)
from app.schemas.skill import SkillBatchImport, SkillCreate, SkillResponse, SkillUpdate
from app.schemas.work_experience import (
    WorkExperienceCreate,
    WorkExperienceResponse,
    WorkExperienceUpdate,
)

__all__ = [
    # common
    "PaginatedResponse",
    "ErrorEnvelope",
    "ErrorDetail",
    "ErrorBody",
    "SuccessResponse",
    "TaskResponse",
    "DataResponse",
    # auth
    "SignupRequest",
    "LoginRequest",
    "RefreshRequest",
    "AuthResponse",
    "SessionResponse",
    "UserResponse",
    "UserSchema",
    "SessionSchema",
    # profile
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "ProfileCompleteness",
    "CloneRequest",
    # job
    "JobResponse",
    "JobCreate",
    "JobStatusUpdate",
    "JobFilters",
    "BulkScoreRequest",
    "DiscoverRequest",
    "ScoreBreakdown",
    # skill
    "SkillCreate",
    "SkillUpdate",
    "SkillResponse",
    "SkillBatchImport",
    # work experience
    "WorkExperienceCreate",
    "WorkExperienceUpdate",
    "WorkExperienceResponse",
    # education
    "EducationCreate",
    "EducationUpdate",
    "EducationResponse",
    # application
    "ApplicationResponse",
    "ApplicationCreate",
    "ApplicationStatusUpdate",
    # review
    "ReviewQueueItem",
    "ReviewQueueItemDetail",
    "ApproveRequest",
    "RejectRequest",
    "RegenerateRequest",
    "BulkApproveRequest",
    "BulkApproveResponse",
    # notification
    "NotificationResponse",
    # file
    "PresignUploadRequest",
    "PresignUploadResponse",
    "ConfirmUploadRequest",
    # ai
    "AIRequest",
    "AIResponse",
    "APIKeyInfo",
    "APIKeyCreate",
    "APIKeyValidation",
    "ModelConfig",
    "ModelConfigUpdate",
    "ProviderConfig",
    "UsageStats",
    # interview
    "InterviewCreate",
    "InterviewUpdate",
    "InterviewResponse",
    # copilot
    "ChatRequest",
    "CopilotMessage",
    # email
    "EmailSettings",
    "EmailScanResult",
    # admin
    "AdminUser",
    "AdminUserDetail",
    "RoleUpdate",
    "SuspendRequest",
    "SystemHealth",
    "FeatureFlags",
    "FeatureFlagUpdate",
]
