"""Copilot service — AI chat with streaming, conversation management, action execution.

Implements copilot logic per API Contract Section 4.9.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.copilot_conversation import CopilotConversation


async def chat_stream(
    db: AsyncSession, user_id: uuid.UUID, message: str,
    context: dict | None, conversation_id: uuid.UUID | None,
) -> AsyncGenerator[str, None]:
    """Stream a copilot response via SSE. Yields text chunks."""
    # 1. Load or create conversation
    if conversation_id:
        result = await db.execute(
            select(CopilotConversation).where(
                CopilotConversation.id == conversation_id,
                CopilotConversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Conversation not found")
    else:
        conversation = CopilotConversation(
            user_id=user_id,
            messages=[],
            context=context,
        )
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)

    # 2. Append user message
    messages = list(conversation.messages or [])
    messages.append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now(UTC).isoformat(),
    })

    # 3. Try to call AI proxy for response
    assistant_content: str
    model_used: str | None = None
    try:
        from app.services.ai_proxy_service import call_ai

        # Build prompt from conversation history
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        system_prompt = (
            "You are a helpful job application assistant. Help the user with their "
            "job search, applications, interview prep, and career questions. "
            "Be concise and actionable."
        )
        if context:
            system_prompt += f"\n\nContext: {context}"

        ai_response = await call_ai(
            db=db,
            user_id=user_id,
            task_type="copilot",
            prompt=history_text,
            system_prompt=system_prompt,
        )
        assistant_content = ai_response.content
        model_used = ai_response.model_used
    except Exception as e:
        logger.warning("AI proxy unavailable for copilot chat: {}", e)
        assistant_content = (
            "I'd love to help you with your job search! However, the AI service is not "
            "currently configured. To enable AI-powered assistance, please add your API key "
            "via the /api/v1/ai/keys endpoint. Once configured, I can help with:\n\n"
            "- Job search strategy and recommendations\n"
            "- Resume and cover letter feedback\n"
            "- Interview preparation\n"
            "- Application tracking advice"
        )

    # 4. Append assistant message
    messages.append({
        "role": "assistant",
        "content": assistant_content,
        "timestamp": datetime.now(UTC).isoformat(),
    })

    # 5. Save conversation to DB
    conversation.messages = messages
    if model_used:
        conversation.model_used = model_used
    if context and not conversation.context:
        conversation.context = context
    await db.flush()
    await db.refresh(conversation)

    logger.info("Copilot chat for user {}, conversation {}", user_id, conversation.id)

    # 6. Yield the response text as SSE chunks (split into words for streaming effect)
    words = assistant_content.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield chunk


async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[CopilotConversation]:
    """List all conversations for a user."""
    result = await db.execute(
        select(CopilotConversation)
        .where(CopilotConversation.user_id == user_id)
        .order_by(CopilotConversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_conversation(db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    """Delete a conversation."""
    result = await db.execute(
        select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Conversation not found")

    await db.delete(conversation)
    await db.flush()
    logger.info("Deleted conversation {} for user {}", conversation_id, user_id)


async def execute_action(db: AsyncSession, user_id: uuid.UUID, action: str, params: dict, token: str) -> dict:
    """Execute a copilot-suggested action after user confirmation."""
    logger.info("Executing copilot action '{}' for user {}", action, user_id)

    try:
        if action == "discover":
            from app.tasks.discovery_tasks import discover_jobs

            profile_id = params.get("profile_id")
            if not profile_id:
                return {"task_id": None, "result": {"message": "Missing profile_id parameter"}}

            result = discover_jobs.delay(str(user_id), str(profile_id))
            return {"task_id": result.id, "result": None}

        elif action == "score":
            from app.tasks.scoring_tasks import score_job

            job_id = params.get("job_id")
            if not job_id:
                return {"task_id": None, "result": {"message": "Missing job_id parameter"}}

            result = score_job.delay(str(user_id), str(job_id))
            return {"task_id": result.id, "result": None}

        elif action == "generate":
            from app.tasks.content_tasks import generate_resume

            job_id = params.get("job_id")
            profile_id = params.get("profile_id")
            if not job_id or not profile_id:
                return {"task_id": None, "result": {"message": "Missing job_id or profile_id parameter"}}

            result = generate_resume.delay(
                str(user_id), str(job_id), str(profile_id),
                params.get("instructions"),
            )
            return {"task_id": result.id, "result": None}

        elif action == "stats":
            from app.models.application import Application

            # Total applications
            total_result = await db.execute(
                select(func.count(Application.id)).where(
                    Application.user_id == user_id,
                )
            )
            total = total_result.scalar() or 0

            # Count by status
            status_result = await db.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.user_id == user_id)
                .group_by(Application.status)
            )
            by_status = {row[0]: row[1] for row in status_result.all()}

            interviews = by_status.get("interview", 0)
            offers = by_status.get("offer", 0)
            rejections = by_status.get("rejected", 0)
            response_rate = round((interviews + offers + rejections) / total * 100, 1) if total > 0 else 0.0

            return {
                "task_id": None,
                "result": {
                    "total": total,
                    "by_status": by_status,
                    "interviews": interviews,
                    "offers": offers,
                    "rejections": rejections,
                    "response_rate": response_rate,
                },
            }

        elif action == "compare":
            from app.models.job import Job

            job_ids = params.get("job_ids")
            if not job_ids or len(job_ids) != 2:
                return {"task_id": None, "result": {"message": "Provide exactly two job_ids to compare"}}

            result_a = await db.execute(
                select(Job).where(Job.id == job_ids[0], Job.user_id == user_id)
            )
            job_a = result_a.scalar_one_or_none()

            result_b = await db.execute(
                select(Job).where(Job.id == job_ids[1], Job.user_id == user_id)
            )
            job_b = result_b.scalar_one_or_none()

            if not job_a or not job_b:
                return {"task_id": None, "result": {"message": "One or both jobs not found"}}

            def _job_summary(job: Job) -> dict:
                salary_range = None
                if job.salary_min or job.salary_max:
                    currency = job.salary_currency or "USD"
                    salary_range = f"{currency} {job.salary_min or '?'} - {job.salary_max or '?'}"
                return {
                    "title": job.title,
                    "company": job.company,
                    "score": job.score,
                    "salary_range": salary_range,
                    "location": job.location,
                    "skills_matched": job.skills_matched,
                    "skills_missing": job.skills_missing,
                }

            return {
                "task_id": None,
                "result": {
                    "job_a": _job_summary(job_a),
                    "job_b": _job_summary(job_b),
                },
            }

        elif action == "help":
            return {
                "task_id": None,
                "result": {
                    "commands": {
                        "/discover": "Trigger job discovery for active profile",
                        "/score": "Score a specific job or bulk score new jobs",
                        "/generate": "Generate resume/cover letter for a job",
                        "/stats": "View your application statistics",
                        "/compare": "Compare two jobs side by side",
                        "/help": "Show available commands",
                    },
                },
            }

        else:
            return {"task_id": None, "result": {"message": f"Unknown action: {action}"}}

    except Exception as e:
        logger.error("Failed to execute copilot action '{}': {}", action, e)
        return {"task_id": None, "result": {"message": f"Failed to execute action: {e}"}}
