"""Profile service — CRUD, cloning, completeness calculation.

Implements business logic for profile management per API Contract Section 4.2.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate


async def list_profiles(db: AsyncSession, user_id: uuid.UUID) -> list[Profile]:
    """List all non-deleted profiles for a user."""
    result = await db.execute(
        select(Profile)
        .where(Profile.user_id == user_id, Profile.is_deleted == False)  # noqa: E712
        .order_by(Profile.created_at.desc())
    )
    return list(result.scalars().all())


async def create_profile(
    db: AsyncSession, user_id: uuid.UUID, data: ProfileCreate
) -> Profile:
    """Create a new profile and compute initial completeness."""
    profile = Profile(
        user_id=user_id,
        **data.model_dump(exclude_none=True),
    )
    db.add(profile)
    await db.flush()

    pct, _ = compute_completeness(profile)
    profile.completeness_pct = pct
    await db.flush()
    await db.refresh(profile)
    return profile


async def get_profile(
    db: AsyncSession, user_id: uuid.UUID, profile_id: uuid.UUID
) -> Profile | None:
    """Get a profile by ID, enforcing user ownership."""
    result = await db.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.user_id == user_id,
            Profile.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def update_profile(
    db: AsyncSession, user_id: uuid.UUID, profile_id: uuid.UUID, data: ProfileUpdate
) -> Profile | None:
    """Update a profile and recompute completeness."""
    profile = await get_profile(db, user_id, profile_id)
    if profile is None:
        return None

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    pct, _ = compute_completeness(profile)
    profile.completeness_pct = pct
    await db.flush()
    await db.refresh(profile)
    return profile


async def delete_profile(
    db: AsyncSession, user_id: uuid.UUID, profile_id: uuid.UUID
) -> bool:
    """Soft-delete a profile. Returns True if found, False if not."""
    profile = await get_profile(db, user_id, profile_id)
    if profile is None:
        return False

    profile.is_deleted = True
    profile.deleted_at = datetime.now(UTC)
    await db.flush()
    return True


async def clone_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    profile_id: uuid.UUID,
    name: str,
    data_types: list[str],
) -> Profile | None:
    """Clone a profile, optionally copying only selected data types."""
    source = await get_profile(db, user_id, profile_id)
    if source is None:
        return None

    # Always copy core fields
    new_profile = Profile(
        user_id=user_id,
        name=name,
        target_role=source.target_role,
        target_seniority=source.target_seniority,
        target_employment_types=source.target_employment_types,
        target_locations=source.target_locations,
        negative_locations=source.negative_locations,
        years_of_experience=source.years_of_experience,
        current_title=source.current_title,
        salary_min=source.salary_min,
        salary_max=source.salary_max,
        salary_currency=source.salary_currency,
        is_active=False,  # cloned profiles start inactive
    )

    # Optionally copy deep profile fields
    copy_all = len(data_types) == 0  # empty = copy everything

    if copy_all or "settings" in data_types:
        new_profile.scoring_weights = source.scoring_weights
        new_profile.automation_config = source.automation_config
        new_profile.discovery_config = source.discovery_config
        new_profile.dream_companies = source.dream_companies
        new_profile.blacklist = source.blacklist
        new_profile.ai_instructions = source.ai_instructions
        new_profile.writing_tones = source.writing_tones
        new_profile.work_preferences = source.work_preferences

    if copy_all or "social" in data_types:
        new_profile.linkedin_url = source.linkedin_url
        new_profile.github_url = source.github_url
        new_profile.portfolio_url = source.portfolio_url
        new_profile.social_urls = source.social_urls
        new_profile.bio_snippet = source.bio_snippet

    if copy_all or "personal" in data_types:
        new_profile.work_authorization = source.work_authorization
        new_profile.languages = source.languages
        new_profile.notice_period = source.notice_period
        new_profile.availability_date = source.availability_date
        new_profile.custom_fields = source.custom_fields

    db.add(new_profile)
    await db.flush()

    pct, _ = compute_completeness(new_profile)
    new_profile.completeness_pct = pct
    await db.flush()
    await db.refresh(new_profile)
    return new_profile


async def activate_profile(
    db: AsyncSession, user_id: uuid.UUID, profile_id: uuid.UUID
) -> Profile | None:
    """Set a profile as active, deactivating all others."""
    profile = await get_profile(db, user_id, profile_id)
    if profile is None:
        return None

    # Deactivate all profiles for this user
    await db.execute(
        update(Profile)
        .where(Profile.user_id == user_id, Profile.is_deleted == False)  # noqa: E712
        .values(is_active=False)
    )

    # Activate the target profile
    profile.is_active = True
    await db.flush()
    await db.refresh(profile)
    return profile


def compute_completeness(profile: Profile) -> tuple[int, list[str]]:
    """Compute profile completeness percentage and list of missing items.

    10 sections, each worth 10 points:
    1. Basic info (name, target_role) — always present since required
    2. Salary expectations
    3. Experience details (years, current_title)
    4. Social links (linkedin, github, portfolio)
    5. Work authorization
    6. Languages
    7. Work preferences
    8. AI instructions
    9. Scoring weights
    10. Discovery config
    """
    missing: list[str] = []
    score = 0

    # 1. Basic info — always present (required fields)
    score += 10

    # 2. Salary expectations
    if profile.salary_min is not None and profile.salary_max is not None:
        score += 10
    else:
        missing.append("salary_expectations")

    # 3. Experience details
    if profile.years_of_experience is not None or profile.current_title is not None:
        score += 10
    else:
        missing.append("experience_details")

    # 4. Social links
    if profile.linkedin_url or profile.github_url or profile.portfolio_url:
        score += 10
    else:
        missing.append("social_links")

    # 5. Work authorization
    if profile.work_authorization and len(profile.work_authorization) > 0:
        score += 10
    else:
        missing.append("work_authorization")

    # 6. Languages
    if profile.languages and len(profile.languages) > 0:
        score += 10
    else:
        missing.append("languages")

    # 7. Work preferences
    if profile.work_preferences and len(profile.work_preferences) > 0:
        score += 10
    else:
        missing.append("work_preferences")

    # 8. AI instructions
    if profile.ai_instructions:
        score += 10
    else:
        missing.append("ai_instructions")

    # 9. Scoring weights
    if profile.scoring_weights and len(profile.scoring_weights) > 0:
        score += 10
    else:
        missing.append("scoring_weights")

    # 10. Discovery config
    if profile.discovery_config and len(profile.discovery_config) > 0:
        score += 10
    else:
        missing.append("discovery_config")

    return score, missing
