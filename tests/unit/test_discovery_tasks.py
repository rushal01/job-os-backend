"""Tests for the discovery pipeline — dedup hash, normalization, mock scraping."""


from app.tasks.discovery_tasks import (
    _mock_scrape,
    compute_dedup_hash,
    normalize_raw_job,
)

# ---------------------------------------------------------------------------
# Dedup hash
# ---------------------------------------------------------------------------

class TestComputeDedupHash:
    def test_deterministic(self):
        h1 = compute_dedup_hash("TechCorp", "Senior Engineer", "SF")
        h2 = compute_dedup_hash("TechCorp", "Senior Engineer", "SF")
        assert h1 == h2

    def test_case_insensitive(self):
        h1 = compute_dedup_hash("TechCorp", "Senior Engineer", "SF")
        h2 = compute_dedup_hash("techcorp", "senior engineer", "sf")
        assert h1 == h2

    def test_strips_whitespace(self):
        h1 = compute_dedup_hash("TechCorp", "Senior Engineer", "SF")
        h2 = compute_dedup_hash("  TechCorp  ", " Senior Engineer ", "  SF  ")
        assert h1 == h2

    def test_different_companies_differ(self):
        h1 = compute_dedup_hash("TechCorp", "Senior Engineer", "SF")
        h2 = compute_dedup_hash("OtherCorp", "Senior Engineer", "SF")
        assert h1 != h2

    def test_none_location(self):
        h1 = compute_dedup_hash("TechCorp", "Senior Engineer", None)
        h2 = compute_dedup_hash("TechCorp", "Senior Engineer", None)
        assert h1 == h2

    def test_hash_is_sha256_hex(self):
        h = compute_dedup_hash("A", "B", "C")
        assert len(h) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class TestNormalizeRawJob:
    def test_strips_whitespace(self):
        raw = {"title": "  Engineer  ", "company": "  Corp  ", "location": "  SF  "}
        result = normalize_raw_job(raw)
        assert result["title"] == "Engineer"
        assert result["company"] == "Corp"
        assert result["location"] == "SF"

    def test_empty_location_becomes_none(self):
        raw = {"title": "Eng", "company": "Corp", "location": "   "}
        result = normalize_raw_job(raw)
        assert result["location"] is None

    def test_missing_fields_default(self):
        raw = {"title": "Eng", "company": "Corp"}
        result = normalize_raw_job(raw)
        assert result["description"] is None
        assert result["skills_required"] == []
        assert result["skills_preferred"] == []

    def test_all_fields_extracted(self):
        raw = {
            "title": "Engineer",
            "company": "Corp",
            "location": "SF",
            "location_type": "remote",
            "seniority": "Senior",
            "employment_type": "Full-time",
            "description": "A job",
            "apply_url": "https://example.com",
            "ats_type": "greenhouse",
            "posted_date": "2024-01-01",
            "salary_min": 100000,
            "salary_max": 200000,
            "salary_currency": "USD",
            "skills_required": ["python"],
            "skills_preferred": ["go"],
        }
        result = normalize_raw_job(raw)
        assert result["location_type"] == "remote"
        assert result["salary_min"] == 100000
        assert result["skills_required"] == ["python"]


# ---------------------------------------------------------------------------
# Mock scraping
# ---------------------------------------------------------------------------

class TestMockScrape:
    def test_returns_results(self):
        results = _mock_scrape(["mock"], ["Backend Engineer"])
        assert len(results) >= 1
        assert results[0]["title"] == "Senior Backend Engineer"
        assert results[0]["company"] == "TechCorp Inc"

    def test_limits_keywords(self):
        results = _mock_scrape(["mock"], ["A", "B", "C"])
        assert len(results) == 1  # only first keyword

    def test_result_has_required_fields(self):
        results = _mock_scrape(["mock"], ["Engineer"])
        r = results[0]
        assert "source" in r
        assert "title" in r
        assert "company" in r
        assert "skills_required" in r
