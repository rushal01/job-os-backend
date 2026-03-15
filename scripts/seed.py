"""Database seed script using Faker for realistic mock data.

Run: python -m scripts.seed
"""

import asyncio
import uuid

from faker import Faker

from app.db.session import async_session
from app.models.user import User, UserRole
from app.models.profile import Profile
from app.models.skill import Skill
from app.models.work_experience import WorkExperience
from app.models.education import Education
from app.models.job import Job
from app.models.notification import Notification

fake = Faker()


async def seed() -> None:
    async with async_session() as session:
        # ─── Users ───
        admin = User(
            id=uuid.uuid4(),
            email="admin@jobapp.test",
            role=UserRole.SUPER_ADMIN,
            full_name="Admin User",
            supabase_uid="test-admin-uid",
            settings={},
        )
        user = User(
            id=uuid.uuid4(),
            email="user@jobapp.test",
            role=UserRole.USER,
            full_name="Test User",
            supabase_uid="test-user-uid",
            settings={},
        )
        session.add_all([admin, user])
        await session.flush()

        # ─── Profiles (3 per user) ───
        profiles = []
        for role in ["Backend Engineer", "ML Engineer", "Platform Engineer"]:
            p = Profile(
                id=uuid.uuid4(),
                user_id=user.id,
                name=f"{role} Search",
                target_role=role,
                target_seniority="Senior (6-10 YOE)",
                years_of_experience=fake.random_int(5, 10),
                salary_min=fake.random_int(150000, 200000),
                salary_max=fake.random_int(200000, 300000),
                completeness_pct=fake.random_int(60, 95),
            )
            profiles.append(p)
        session.add_all(profiles)
        await session.flush()

        # ─── Skills (20 per user) ───
        skill_names = [
            "Python", "TypeScript", "Go", "Rust", "React", "Next.js",
            "FastAPI", "Django", "PostgreSQL", "Redis", "Docker", "Kubernetes",
            "AWS", "GCP", "Terraform", "GraphQL", "gRPC", "Kafka",
            "PyTorch", "TensorFlow",
        ]
        for name in skill_names:
            category = "language" if name in ["Python", "TypeScript", "Go", "Rust"] else "framework"
            session.add(Skill(
                id=uuid.uuid4(),
                user_id=user.id,
                name=name,
                category=category,
                proficiency=fake.random_int(2, 5),
                years_used=float(fake.random_int(1, 8)),
            ))

        # ─── Work Experience (3) ───
        for _ in range(3):
            session.add(WorkExperience(
                id=uuid.uuid4(),
                user_id=user.id,
                company=fake.company(),
                title=fake.job(),
                start_date=fake.date_between(start_date="-6y", end_date="-2y").isoformat(),
                end_date=fake.date_between(start_date="-2y", end_date="today").isoformat(),
                is_current=False,
                location=fake.city(),
                description=fake.paragraph(nb_sentences=3),
            ))

        # ─── Education (1) ───
        session.add(Education(
            id=uuid.uuid4(),
            user_id=user.id,
            institution=fake.company() + " University",
            degree="Bachelor of Science",
            field="Computer Science",
            start_date="2012-09",
            end_date="2016-06",
        ))

        # ─── Jobs (100) ───
        companies = [
            "Google", "Stripe", "Meta", "Netflix", "Airbnb", "Uber",
            "Databricks", "Figma", "Vercel", "Supabase", "Linear",
            "Anthropic", "OpenAI", "Datadog", "Cloudflare",
        ]
        for _ in range(100):
            session.add(Job(
                id=uuid.uuid4(),
                user_id=user.id,
                profile_id=profiles[0].id,
                title=fake.job(),
                company=fake.random_element(companies),
                location=fake.city(),
                location_type=fake.random_element(["remote", "hybrid_flex", "onsite"]),
                seniority="Senior",
                employment_type="Full-time",
                score=round(fake.pyfloat(min_value=30, max_value=98), 1),
                confidence=round(fake.pyfloat(min_value=0.5, max_value=0.99), 2),
                status=fake.random_element(["new", "scored", "content_ready", "applied"]),
                salary_min=fake.random_int(150000, 200000),
                salary_max=fake.random_int(200000, 350000),
                salary_currency="USD",
            ))

        # ─── Notifications (30) ───
        notification_types = [
            "job_scored", "content_ready", "application_submitted",
            "discovery_complete", "task_failed",
        ]
        for _ in range(30):
            session.add(Notification(
                id=uuid.uuid4(),
                user_id=user.id,
                type=fake.random_element(notification_types),
                priority=fake.random_element(["critical", "high", "medium", "low"]),
                title=fake.sentence(nb_words=6),
                body=fake.paragraph(nb_sentences=2),
                read=fake.boolean(chance_of_getting_true=40),
            ))

        await session.commit()
        from loguru import logger
        logger.info("Seed complete: 2 users, 3 profiles, 20 skills, 100 jobs, 30 notifications")


if __name__ == "__main__":
    asyncio.run(seed())
