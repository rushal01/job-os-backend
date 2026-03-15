"""Tests for content generation service — QA checks and quality scoring."""


from app.services.content_service import calculate_quality_score, run_qa_check

# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

class TestCalculateQualityScore:
    def test_high_quality_resume(self):
        content = (
            "# Senior Backend Engineer Resume\n\n"
            "## Professional Summary\n\n"
            "Experienced backend engineer with 8 years building scalable distributed systems "
            "using Python, Go, and Kubernetes. Led team of 5 engineers at TechCorp delivering "
            "microservices handling 10M+ requests/day.\n\n"
            "## Technical Skills\n\n"
            "Python, Go, PostgreSQL, Redis, Docker, Kubernetes, AWS, Terraform, CI/CD, "
            "GraphQL, REST APIs, gRPC, Message Queues, Monitoring\n\n"
            "## Experience\n\n"
            "Senior Engineer at TechCorp (2020-2024)\n"
            "- Designed and implemented event-driven architecture reducing latency by 40%\n"
            "- Built real-time data pipeline processing 5TB/day\n"
            "- Mentored 3 junior engineers through onboarding and career growth\n\n"
            "Software Engineer at StartupCo (2016-2020)\n"
            "- Developed core API serving 1M+ users with 99.9% uptime\n"
            "- Migrated monolith to microservices architecture\n\n"
            "## Education\n\n"
            "BS Computer Science, Stanford University"
        )
        score, breakdown = calculate_quality_score(content, "resume_v1")
        assert score >= 80
        assert breakdown["structure"] >= 20

    def test_low_quality_content(self):
        content = "Hello world"
        score, breakdown = calculate_quality_score(content, "resume_v1")
        assert score < 50

    def test_placeholder_detected(self):
        content = (
            "Professional Summary\n\n"
            "[INSERT YOUR NAME HERE]\n\n"
            "Skills and experience in software development."
        )
        score, breakdown = calculate_quality_score(content, "resume_v1")
        assert breakdown["completeness"] == 5

    def test_cover_letter_scoring(self):
        content = (
            "Dear Hiring Manager,\n\n"
            "I am writing to express my interest in the Senior Backend Engineer position "
            "at Anthropic. With 8 years of experience in distributed systems and a passion "
            "for AI safety, I believe I would be a strong addition to your team.\n\n"
            "In my current role at TechCorp, I have led the development of microservices "
            "that handle millions of requests daily. My experience with Python and cloud "
            "infrastructure aligns well with the requirements of this position.\n\n"
            "I would welcome the opportunity to discuss how my background can contribute "
            "to Anthropic's mission. Thank you for your consideration.\n\n"
            "Best regards,\nTest User"
        )
        score, breakdown = calculate_quality_score(content, "cover_letter")
        assert score >= 60


# ---------------------------------------------------------------------------
# QA checks
# ---------------------------------------------------------------------------

class TestRunQACheck:
    def test_passes_good_content(self):
        content = (
            "Professional Summary\n\n"
            "Experienced engineer with deep expertise in building scalable systems. "
            "Strong background in Python, Go, and cloud infrastructure with proven "
            "track record of delivering high-impact projects."
        )
        report = run_qa_check(content, "resume_v1")
        assert report["passed"] is True
        assert len(report["issues"]) == 0

    def test_fails_too_short(self):
        report = run_qa_check("Hello world", "resume_v1")
        assert report["passed"] is False
        assert any("too short" in i for i in report["issues"])

    def test_warns_placeholder(self):
        content = "Some content here [your name] and more text that makes it long enough to pass the length check."
        report = run_qa_check(content, "resume_v1")
        assert report["passed"] is False
        assert any("placeholder" in i.lower() for i in report["issues"])

    def test_cover_letter_missing_greeting(self):
        content = (
            "I am writing about the position. " * 20
        )
        report = run_qa_check(content, "cover_letter")
        # Should warn about missing greeting
        assert any("greeting" in w.lower() for w in report["warnings"])

    def test_cover_letter_too_long(self):
        content = ("Word " * 700).strip()
        report = run_qa_check(content, "cover_letter")
        assert any("too long" in w.lower() for w in report["warnings"])

    def test_word_count_tracked(self):
        content = "one two three four five"
        report = run_qa_check(content, "answer")
        assert report["word_count"] == 5
