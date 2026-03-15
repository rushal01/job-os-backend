"""Scoring service — 8-dimension job-profile match scoring engine.

Computes skill, title, seniority, location, salary, company, culture, and
freshness scores with configurable weights. Produces a composite score (0-100),
confidence (0-1), risk score (0-1), and decision (auto_apply/review/skip).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.profile import Profile
from app.models.skill import Skill

# ---------------------------------------------------------------------------
# Default weights (sum to 100)
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: dict[str, float] = {
    "skill": 30,
    "title": 20,
    "seniority": 15,
    "location": 10,
    "salary": 10,
    "company": 8,
    "culture": 4,
    "freshness": 3,
}

SENIORITY_LEVELS = [
    "intern", "junior", "mid", "mid-level", "senior", "staff", "principal", "director", "vp", "c-level",
]


@dataclass
class ScoreResult:
    """Result of scoring a job against a profile."""
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    confidence: float = 0.0
    risk_score: float = 0.0
    decision: str = "skip"
    decision_reasoning: str = ""
    skills_matched: list[str] = field(default_factory=list)
    skills_missing: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 8 scoring dimensions
# ---------------------------------------------------------------------------

def skill_score(job: Job, user_skills: list[Skill]) -> tuple[float, list[str], list[str]]:
    """Dimension 1: Compare job.skills_required against user skills.

    Returns (score, matched, missing).
    """
    required = [s.lower().strip() for s in (job.skills_required or [])]
    preferred = [s.lower().strip() for s in (job.skills_preferred or [])]
    user_skill_names = {s.name.lower().strip() for s in user_skills}

    if not required and not preferred:
        return 50.0, [], []  # No data → neutral

    matched = []
    missing = []

    # Required skills: full weight
    req_points = 0.0
    for skill in required:
        if skill in user_skill_names:
            matched.append(skill)
            req_points += 1.0
        elif _fuzzy_skill_match(skill, user_skill_names):
            matched.append(skill)
            req_points += 0.5
        else:
            missing.append(skill)

    # Preferred skills: half weight
    pref_points = 0.0
    for skill in preferred:
        if skill in user_skill_names or _fuzzy_skill_match(skill, user_skill_names):
            pref_points += 1.0

    total_weight = len(required) * 2 + len(preferred)  # required worth 2x
    if total_weight == 0:
        return 50.0, matched, missing

    raw = (req_points * 2 + pref_points) / total_weight * 100
    return min(raw, 100.0), matched, missing


def _fuzzy_skill_match(skill: str, user_skills: set[str], threshold: float = 0.7) -> bool:
    """Check if any user skill is similar enough to count as a partial match."""
    for us in user_skills:
        if SequenceMatcher(None, skill, us).ratio() >= threshold:
            return True
    return False


def title_score(job: Job, profile: Profile) -> float:
    """Dimension 2: Fuzzy match job.title against profile.target_role."""
    if not job.title or not profile.target_role:
        return 50.0

    job_title = job.title.lower().strip()
    target = profile.target_role.lower().strip()

    if job_title == target:
        return 100.0

    ratio = SequenceMatcher(None, job_title, target).ratio()
    # Scale: ratio 0.8+ → 90+, 0.6-0.8 → 60-90, below → 20-60
    if ratio >= 0.8:
        return 80 + ratio * 20
    elif ratio >= 0.5:
        return 40 + ratio * 50
    else:
        return max(20.0, ratio * 60)


def seniority_score(job: Job, profile: Profile) -> float:
    """Dimension 3: Compare seniority levels."""
    if not job.seniority or not profile.target_seniority:
        return 50.0

    job_level = _normalize_seniority(job.seniority)
    profile_level = _normalize_seniority(profile.target_seniority)

    job_idx = _seniority_index(job_level)
    profile_idx = _seniority_index(profile_level)

    if job_idx == -1 or profile_idx == -1:
        return 50.0

    diff = abs(job_idx - profile_idx)
    if diff == 0:
        return 100.0
    elif diff == 1:
        return 60.0
    else:
        return max(20.0, 100.0 - diff * 30)


def _normalize_seniority(s: str) -> str:
    """Normalize seniority string to a standard level."""
    s = s.lower().strip()
    if "intern" in s:
        return "intern"
    if "junior" in s or "entry" in s or "jr" in s:
        return "junior"
    if "senior" in s or "sr" in s:
        return "senior"
    if "staff" in s:
        return "staff"
    if "principal" in s or "distinguished" in s:
        return "principal"
    if "director" in s:
        return "director"
    if "vp" in s or "vice" in s:
        return "vp"
    if "mid" in s:
        return "mid-level"
    return "mid-level"  # default


def _seniority_index(level: str) -> int:
    """Get numeric index for a seniority level."""
    try:
        return SENIORITY_LEVELS.index(level)
    except ValueError:
        return -1


def location_score(job: Job, profile: Profile) -> float:
    """Dimension 4: Location match including remote preference and negative list."""
    target_locations = [loc.lower().strip() for loc in (profile.target_locations or [])]
    negative_locations = [loc.lower().strip() for loc in (profile.negative_locations or [])]
    job_location = (job.location or "").lower().strip()
    job_type = (job.location_type or "").lower().strip()

    # Check negative locations first
    for neg in negative_locations:
        if neg and neg in job_location:
            return 0.0

    # Remote match
    if "remote" in job_type:
        if "remote" in " ".join(target_locations) or not target_locations:
            return 100.0
        return 80.0  # Remote is generally good

    if not target_locations or not job_location:
        return 50.0

    # City/location match
    for target in target_locations:
        if target in job_location or job_location in target:
            return 100.0

    return 30.0  # No match


def salary_score(job: Job, profile: Profile) -> float:
    """Dimension 5: Salary range overlap."""
    if not job.salary_min and not job.salary_max:
        return 50.0  # No data
    if not profile.salary_min and not profile.salary_max:
        return 50.0

    job_min = job.salary_min or 0
    job_max = job.salary_max or job_min
    prof_min = profile.salary_min or 0
    prof_max = profile.salary_max or prof_min

    if job_max == 0 or prof_max == 0:
        return 50.0

    # Calculate overlap
    overlap_min = max(job_min, prof_min)
    overlap_max = min(job_max, prof_max)

    if overlap_min > overlap_max:
        # No overlap — how far apart?
        gap = overlap_min - overlap_max
        range_size = max(prof_max - prof_min, 1)
        return max(0.0, 50.0 - (gap / range_size) * 50)

    overlap = overlap_max - overlap_min
    total_range = max(prof_max - prof_min, 1)
    return min(100.0, (overlap / total_range) * 100)


def company_score(job: Job, profile: Profile) -> float:
    """Dimension 6: Dream company / blacklist / company intel."""
    company = (job.company or "").lower().strip()
    dream = [c.lower().strip() for c in (profile.dream_companies or [])]
    blacklist = [c.lower().strip() for c in (profile.blacklist or [])]

    for bl in blacklist:
        if bl and bl in company:
            return 0.0

    for dc in dream:
        if dc and dc in company:
            return 100.0

    # Use company intel if available
    intel = job.company_intel or {}
    if intel:
        rating = intel.get("glassdoor_rating", 0)
        if rating >= 4.0:
            return 75.0
        elif rating >= 3.0:
            return 55.0

    return 50.0  # No data → neutral


def culture_score(job: Job, profile: Profile) -> float:
    """Dimension 7: Culture alignment from company intel."""
    intel = job.company_intel or {}
    prefs = profile.work_preferences or {}

    if not intel and not prefs:
        return 50.0  # No data → neutral

    points = 0
    checks = 0

    # Glassdoor rating
    if "glassdoor_rating" in intel:
        checks += 1
        rating = intel["glassdoor_rating"]
        if rating >= 4.0:
            points += 1
        elif rating >= 3.0:
            points += 0.5

    # Work-life balance
    if "work_life_balance" in intel:
        checks += 1
        if intel["work_life_balance"] >= 3.5:
            points += 1
        elif intel["work_life_balance"] >= 2.5:
            points += 0.5

    if checks == 0:
        return 50.0

    return (points / checks) * 100


def freshness_score(job: Job) -> float:
    """Dimension 8: How fresh is the job posting."""
    if not job.posted_date:
        return 50.0  # Unknown → neutral

    try:
        posted = datetime.fromisoformat(job.posted_date.replace("Z", "+00:00"))
        days_old = (datetime.now(timezone.utc) - posted).days
    except (ValueError, TypeError):
        return 50.0

    if days_old <= 3:
        return 100.0
    elif days_old <= 7:
        return 80.0
    elif days_old <= 14:
        return 60.0
    elif days_old <= 30:
        return 30.0
    else:
        return 10.0


# ---------------------------------------------------------------------------
# Confidence & Risk
# ---------------------------------------------------------------------------

def compute_confidence(job: Job) -> float:
    """Compute confidence 0-1 based on data completeness."""
    factors = []
    factors.append(1.0 if job.description else 0.3)
    factors.append(1.0 if job.salary_min else 0.5)
    factors.append(0.7 if getattr(job, "salary_estimated", False) else 1.0)
    factors.append(1.0 if job.location else 0.5)
    factors.append(1.0 if job.skills_required else 0.4)
    factors.append(1.0 if job.company_intel else 0.5)
    return round(sum(factors) / len(factors), 2)


def compute_risk(job: Job, profile: Profile, skills_missing: list[str]) -> float:
    """Compute risk score 0-1."""
    risk = 0.0
    total_factors = 5

    # Old posting
    if job.posted_date:
        try:
            posted = datetime.fromisoformat(job.posted_date.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - posted).days > 30:
                risk += 1.0
        except (ValueError, TypeError):
            pass

    # Missing required skills
    required_count = len(job.skills_required or [])
    if required_count > 0 and len(skills_missing) > required_count * 0.5:
        risk += 1.0

    # Seniority mismatch
    if job.seniority and profile.target_seniority:
        j_idx = _seniority_index(_normalize_seniority(job.seniority))
        p_idx = _seniority_index(_normalize_seniority(profile.target_seniority))
        if j_idx >= 0 and p_idx >= 0 and abs(j_idx - p_idx) > 1:
            risk += 1.0

    # No salary
    if not job.salary_min and not job.salary_max:
        risk += 0.5

    # Blacklisted company signals
    blacklist = [c.lower() for c in (profile.blacklist or [])]
    company = (job.company or "").lower()
    for bl in blacklist:
        if bl and bl in company:
            risk += 1.0

    return round(min(risk / total_factors, 1.0), 2)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def score_job(
    db: AsyncSession, job: Job, profile: Profile, user_skills: list[Skill] | None = None
) -> ScoreResult:
    """Orchestrator — calls all 8 dimensions, computes weighted total, determines decision."""
    if user_skills is None:
        user_skills = []

    # Get weights (from profile or defaults)
    weights = dict(DEFAULT_WEIGHTS)
    if profile.scoring_weights:
        for k, v in profile.scoring_weights.items():
            if k in weights:
                weights[k] = float(v)

    # Compute each dimension
    s_skill, matched, missing = skill_score(job, user_skills)
    s_title = title_score(job, profile)
    s_seniority = seniority_score(job, profile)
    s_location = location_score(job, profile)
    s_salary = salary_score(job, profile)
    s_company = company_score(job, profile)
    s_culture = culture_score(job, profile)
    s_freshness = freshness_score(job)

    breakdown = {
        "skill": round(s_skill, 1),
        "title": round(s_title, 1),
        "seniority": round(s_seniority, 1),
        "location": round(s_location, 1),
        "salary": round(s_salary, 1),
        "company": round(s_company, 1),
        "culture": round(s_culture, 1),
        "freshness": round(s_freshness, 1),
    }

    # Weighted average
    scores = {
        "skill": s_skill, "title": s_title, "seniority": s_seniority,
        "location": s_location, "salary": s_salary, "company": s_company,
        "culture": s_culture, "freshness": s_freshness,
    }
    weight_sum = sum(weights.values())
    total = sum(scores[k] * weights[k] for k in weights) / max(weight_sum, 1)

    # Bonus points
    bonus = 0.0
    company_lower = (job.company or "").lower()
    dream = [c.lower() for c in (profile.dream_companies or [])]
    is_dream = any(d and d in company_lower for d in dream)
    if is_dream:
        bonus += 10
    intel = job.company_intel or {}
    if intel.get("glassdoor_rating", 0) > 4.0:
        bonus += 5

    total = min(total + bonus, 100.0)

    # Confidence & risk
    confidence = compute_confidence(job)
    risk = compute_risk(job, profile, missing)

    # Decision routing
    if total >= 82 and confidence >= 0.7 and risk < 0.3:
        decision = "auto_apply"
        reasoning = f"High score ({total:.0f}), high confidence ({confidence:.2f}), low risk ({risk:.2f})"
    elif total >= 60:
        decision = "review"
        reasoning = f"Moderate score ({total:.0f}), needs human review"
    else:
        decision = "skip"
        reasoning = f"Low score ({total:.0f})"

    # Override: dream companies never get auto-skipped
    if is_dream and decision == "skip":
        decision = "review"
        reasoning += " — overridden: dream company"

    return ScoreResult(
        score=round(total, 1),
        score_breakdown=breakdown,
        confidence=confidence,
        risk_score=risk,
        decision=decision,
        decision_reasoning=reasoning,
        skills_matched=matched,
        skills_missing=missing,
    )


async def bulk_score_jobs(
    db: AsyncSession, user_id: uuid.UUID, job_ids: list[uuid.UUID]
) -> str:
    """Queue bulk scoring as a Celery task. Returns task_id."""
    from app.models.task import Task
    task = Task(
        user_id=user_id,
        task_name="bulk_score_jobs",
        status="pending",
        progress_pct=0.0,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Enqueue Celery task
    from app.tasks.scoring_tasks import bulk_score_jobs as celery_task
    result = celery_task.delay(str(user_id), [str(j) for j in job_ids])
    task.celery_task_id = result.id
    await db.flush()

    return str(task.id)
