"""Tests for the 8-dimension scoring engine."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.services.scoring_service import (
    ScoreResult,
    company_score,
    compute_confidence,
    compute_risk,
    culture_score,
    freshness_score,
    location_score,
    salary_score,
    score_job,
    seniority_score,
    skill_score,
    title_score,
)


def _mock_job(**overrides):
    job = MagicMock()
    job.title = overrides.get("title", "Senior Backend Engineer")
    job.company = overrides.get("company", "TechCorp")
    job.location = overrides.get("location", "San Francisco, CA")
    job.location_type = overrides.get("location_type", "hybrid")
    job.seniority = overrides.get("seniority", "Senior")
    job.employment_type = overrides.get("employment_type", "Full-time")
    job.description = overrides.get("description", "Looking for a skilled engineer.")
    job.posted_date = overrides.get("posted_date", datetime.now(UTC).isoformat())
    job.salary_min = overrides.get("salary_min", 150000)
    job.salary_max = overrides.get("salary_max", 200000)
    job.salary_currency = overrides.get("salary_currency", "USD")
    job.salary_estimated = overrides.get("salary_estimated", False)
    job.skills_required = overrides.get("skills_required", ["python", "sql", "docker"])
    job.skills_preferred = overrides.get("skills_preferred", ["kubernetes", "aws"])
    job.company_intel = overrides.get("company_intel")
    return job


def _mock_profile(**overrides):
    profile = MagicMock()
    profile.target_role = overrides.get("target_role", "Backend Engineer")
    profile.target_seniority = overrides.get("target_seniority", "Senior")
    profile.target_locations = overrides.get("target_locations", ["San Francisco, CA", "Remote"])
    profile.negative_locations = overrides.get("negative_locations", [])
    profile.salary_min = overrides.get("salary_min", 140000)
    profile.salary_max = overrides.get("salary_max", 220000)
    profile.dream_companies = overrides.get("dream_companies", ["Anthropic", "Google"])
    profile.blacklist = overrides.get("blacklist", ["BadCorp"])
    profile.scoring_weights = overrides.get("scoring_weights", {})
    profile.work_preferences = overrides.get("work_preferences", {})
    return profile


class _FakeSkill:
    def __init__(self, name: str):
        self.name = name


def _mock_skill(name: str):
    return _FakeSkill(name)


# ---------------------------------------------------------------------------
# Dimension 1: Skill score
# ---------------------------------------------------------------------------

class TestSkillScore:
    def test_all_skills_matched(self):
        job = _mock_job(skills_required=["python", "sql"], skills_preferred=["aws"])
        user_skills = [_mock_skill("python"), _mock_skill("sql"), _mock_skill("aws")]
        score, matched, missing = skill_score(job, user_skills)
        assert score == 100.0
        assert "python" in matched
        assert "sql" in matched
        assert missing == []

    def test_no_skills_matched(self):
        job = _mock_job(skills_required=["java", "scala"], skills_preferred=["spark"])
        user_skills = [_mock_skill("python"), _mock_skill("sql")]
        score, matched, missing = skill_score(job, user_skills)
        assert score < 20
        assert "java" in missing

    def test_partial_match(self):
        job = _mock_job(skills_required=["python", "java"], skills_preferred=[])
        user_skills = [_mock_skill("python")]
        score, matched, missing = skill_score(job, user_skills)
        assert 40 <= score <= 60
        assert "python" in matched
        assert "java" in missing

    def test_no_requirements(self):
        job = _mock_job(skills_required=[], skills_preferred=[])
        score, matched, missing = skill_score(job, [])
        assert score == 50.0  # Neutral


# ---------------------------------------------------------------------------
# Dimension 2: Title score
# ---------------------------------------------------------------------------

class TestTitleScore:
    def test_exact_match(self):
        job = _mock_job(title="Backend Engineer")
        profile = _mock_profile(target_role="Backend Engineer")
        assert title_score(job, profile) == 100.0

    def test_similar_title(self):
        job = _mock_job(title="Senior Backend Engineer")
        profile = _mock_profile(target_role="Backend Engineer")
        score = title_score(job, profile)
        assert score >= 60  # High similarity

    def test_different_title(self):
        job = _mock_job(title="Marketing Manager")
        profile = _mock_profile(target_role="Backend Engineer")
        score = title_score(job, profile)
        assert score < 50


# ---------------------------------------------------------------------------
# Dimension 3: Seniority score
# ---------------------------------------------------------------------------

class TestSeniorityScore:
    def test_exact_seniority_match(self):
        job = _mock_job(seniority="Senior")
        profile = _mock_profile(target_seniority="Senior")
        assert seniority_score(job, profile) == 100.0

    def test_one_level_off(self):
        job = _mock_job(seniority="Staff")
        profile = _mock_profile(target_seniority="Senior")
        assert seniority_score(job, profile) == 60.0

    def test_no_seniority_data(self):
        job = _mock_job(seniority=None)
        profile = _mock_profile(target_seniority="Senior")
        assert seniority_score(job, profile) == 50.0


# ---------------------------------------------------------------------------
# Dimension 4: Location score
# ---------------------------------------------------------------------------

class TestLocationScore:
    def test_remote_job_remote_pref(self):
        job = _mock_job(location_type="remote")
        profile = _mock_profile(target_locations=["Remote"])
        assert location_score(job, profile) == 100.0

    def test_city_match(self):
        job = _mock_job(location="San Francisco, CA", location_type="hybrid")
        profile = _mock_profile(target_locations=["San Francisco, CA"])
        assert location_score(job, profile) == 100.0

    def test_negative_location(self):
        job = _mock_job(location="New York, NY")
        profile = _mock_profile(negative_locations=["New York"])
        assert location_score(job, profile) == 0.0

    def test_no_match(self):
        job = _mock_job(location="Chicago, IL", location_type="onsite")
        profile = _mock_profile(target_locations=["San Francisco, CA"])
        assert location_score(job, profile) == 30.0


# ---------------------------------------------------------------------------
# Dimension 5: Salary score
# ---------------------------------------------------------------------------

class TestSalaryScore:
    def test_full_overlap(self):
        job = _mock_job(salary_min=150000, salary_max=200000)
        profile = _mock_profile(salary_min=140000, salary_max=220000)
        score = salary_score(job, profile)
        assert score >= 60

    def test_no_overlap(self):
        job = _mock_job(salary_min=50000, salary_max=70000)
        profile = _mock_profile(salary_min=150000, salary_max=220000)
        score = salary_score(job, profile)
        assert score < 30

    def test_no_salary_data(self):
        job = _mock_job(salary_min=None, salary_max=None)
        profile = _mock_profile()
        assert salary_score(job, profile) == 50.0


# ---------------------------------------------------------------------------
# Dimension 6: Company score
# ---------------------------------------------------------------------------

class TestCompanyScore:
    def test_dream_company(self):
        job = _mock_job(company="Anthropic")
        profile = _mock_profile(dream_companies=["Anthropic"])
        assert company_score(job, profile) == 100.0

    def test_blacklisted_company(self):
        job = _mock_job(company="BadCorp Inc")
        profile = _mock_profile(blacklist=["BadCorp"])
        assert company_score(job, profile) == 0.0

    def test_neutral_company(self):
        job = _mock_job(company="RandomCo")
        profile = _mock_profile(dream_companies=[], blacklist=[])
        assert company_score(job, profile) == 50.0


# ---------------------------------------------------------------------------
# Dimension 7: Culture score
# ---------------------------------------------------------------------------

class TestCultureScore:
    def test_high_glassdoor(self):
        job = _mock_job(company_intel={"glassdoor_rating": 4.5})
        profile = _mock_profile()
        assert culture_score(job, profile) == 100.0

    def test_no_data(self):
        job = _mock_job(company_intel=None)
        profile = _mock_profile(work_preferences={})
        assert culture_score(job, profile) == 50.0


# ---------------------------------------------------------------------------
# Dimension 8: Freshness score
# ---------------------------------------------------------------------------

class TestFreshnessScore:
    def test_very_fresh(self):
        job = _mock_job(posted_date=datetime.now(UTC).isoformat())
        assert freshness_score(job) == 100.0

    def test_week_old(self):
        date = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        job = _mock_job(posted_date=date)
        assert freshness_score(job) == 80.0

    def test_old_posting(self):
        date = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        job = _mock_job(posted_date=date)
        assert freshness_score(job) == 10.0

    def test_no_date(self):
        job = _mock_job(posted_date=None)
        assert freshness_score(job) == 50.0


# ---------------------------------------------------------------------------
# Confidence & Risk
# ---------------------------------------------------------------------------

class TestConfidenceAndRisk:
    def test_high_confidence(self):
        job = _mock_job(
            description="Full description",
            salary_min=150000,
            location="SF",
            skills_required=["python"],
            company_intel={"glassdoor_rating": 4.0},
        )
        conf = compute_confidence(job)
        assert conf >= 0.7

    def test_low_confidence(self):
        job = _mock_job(
            description=None,
            salary_min=None,
            location=None,
            skills_required=[],
            company_intel=None,
        )
        conf = compute_confidence(job)
        assert conf < 0.6

    def test_risk_blacklist(self):
        job = _mock_job(company="BadCorp", skills_required=["python"])
        profile = _mock_profile(blacklist=["badcorp"])
        risk = compute_risk(job, profile, [])
        assert risk > 0

    def test_risk_missing_skills(self):
        job = _mock_job(skills_required=["python", "java", "scala", "go"])
        profile = _mock_profile()
        risk = compute_risk(job, profile, ["java", "scala", "go"])
        assert risk > 0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TestScoreJobOrchestrator:
    @pytest.mark.asyncio
    async def test_score_high_match(self):
        job = _mock_job(
            company="Anthropic",
            skills_required=["python", "sql"],
            skills_preferred=["docker"],
            company_intel={"glassdoor_rating": 4.5},
        )
        profile = _mock_profile(
            target_role="Backend Engineer",
            dream_companies=["Anthropic"],
        )
        skills = [_mock_skill("python"), _mock_skill("sql"), _mock_skill("docker")]

        result = await score_job(MagicMock(), job, profile, skills)
        assert isinstance(result, ScoreResult)
        assert result.score >= 70
        assert result.decision in ("auto_apply", "review")

    @pytest.mark.asyncio
    async def test_score_low_match(self):
        job = _mock_job(
            title="Marketing Manager",
            company="RandomCo",
            seniority="Junior",
            skills_required=["photoshop", "figma"],
            location="Nowhere, TX",
            location_type="onsite",
            salary_min=30000,
            salary_max=40000,
            company_intel=None,
        )
        profile = _mock_profile(
            target_role="Backend Engineer",
            target_seniority="Senior",
        )
        skills = [_mock_skill("python"), _mock_skill("sql")]

        result = await score_job(MagicMock(), job, profile, skills)
        assert result.score < 60
        assert result.decision in ("skip", "review")

    @pytest.mark.asyncio
    async def test_dream_company_override(self):
        """Dream companies should never get auto-skipped."""
        job = _mock_job(
            title="Janitor",
            company="Anthropic",
            skills_required=["mop"],
            location="Nowhere",
            location_type="onsite",
            salary_min=20000,
            salary_max=25000,
        )
        profile = _mock_profile(dream_companies=["Anthropic"])

        result = await score_job(MagicMock(), job, profile, [])
        # Even with a terrible match, dream company ensures at least "review"
        assert result.decision in ("review", "auto_apply")

    @pytest.mark.asyncio
    async def test_custom_weights(self):
        """Profile can override scoring weights."""
        job = _mock_job(skills_required=["python"], skills_preferred=[])
        profile = _mock_profile(scoring_weights={"skill": 50, "title": 10})
        skills = [_mock_skill("python")]

        result = await score_job(MagicMock(), job, profile, skills)
        assert isinstance(result, ScoreResult)
        # Skill score should be high since python matches
        assert result.score_breakdown["skill"] == 100.0
