from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.ai import router as ai_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.content import router as content_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.education import router as education_router
from app.api.v1.email import router as email_router
from app.api.v1.files import router as files_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.market import router as market_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.outreach import router as outreach_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.review import router as review_router
from app.api.v1.settings import router as settings_router
from app.api.v1.skills import router as skills_router
from app.api.v1.work_experience import router as work_experience_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router, tags=["auth"])
api_v1_router.include_router(profiles_router, tags=["profiles"])
api_v1_router.include_router(jobs_router, tags=["jobs"])
api_v1_router.include_router(content_router, tags=["content"])
api_v1_router.include_router(applications_router, tags=["applications"])
api_v1_router.include_router(review_router, tags=["review"])
api_v1_router.include_router(outreach_router, tags=["outreach"])
api_v1_router.include_router(email_router, tags=["email"])
api_v1_router.include_router(interviews_router, tags=["interviews"])
api_v1_router.include_router(analytics_router, tags=["analytics"])
api_v1_router.include_router(market_router, tags=["market"])
api_v1_router.include_router(ai_router, tags=["ai"])
api_v1_router.include_router(files_router, tags=["files"])
api_v1_router.include_router(copilot_router, tags=["copilot"])
api_v1_router.include_router(notifications_router, tags=["notifications"])
api_v1_router.include_router(skills_router, tags=["skills"])
api_v1_router.include_router(work_experience_router, tags=["work-experience"])
api_v1_router.include_router(education_router, tags=["education"])
api_v1_router.include_router(admin_router, tags=["admin"])
api_v1_router.include_router(settings_router, tags=["settings"])
