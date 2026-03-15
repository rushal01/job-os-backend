"""Tests for AI proxy service — provider routing, cost calculation, formatters."""



from app.services.ai_proxy_service import (
    COST_TABLE,
    TASK_MODEL_MAP,
    _calculate_cost,
    _format_anthropic_request,
    _format_openai_request,
    _parse_anthropic_response,
    _parse_openai_response,
)

# ---------------------------------------------------------------------------
# Request formatters
# ---------------------------------------------------------------------------

class TestFormatAnthropicRequest:
    def test_basic_request(self):
        headers, body = _format_anthropic_request(
            "Hello", None, "claude-sonnet-4-20250514", 1024, 0.7,
        )
        assert body["model"] == "claude-sonnet-4-20250514"
        assert body["max_tokens"] == 1024
        assert body["messages"][0]["content"] == "Hello"
        assert "system" not in body
        assert "x-api-key" in headers

    def test_with_system_prompt(self):
        headers, body = _format_anthropic_request(
            "Hello", "Be helpful", "claude-sonnet-4-20250514", 1024, 0.7,
        )
        assert body["system"] == "Be helpful"


class TestFormatOpenAIRequest:
    def test_basic_request(self):
        headers, body = _format_openai_request(
            "Hello", None, "gpt-4o-mini", 1024, 0.7,
        )
        assert body["model"] == "gpt-4o-mini"
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        assert "authorization" in headers

    def test_with_system_prompt(self):
        headers, body = _format_openai_request(
            "Hello", "Be helpful", "gpt-4o-mini", 1024, 0.7,
        )
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------

class TestParseAnthropicResponse:
    def test_parse_success(self):
        data = {
            "content": [{"text": "Hello back!"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        content, inp, out = _parse_anthropic_response(data)
        assert content == "Hello back!"
        assert inp == 10
        assert out == 20


class TestParseOpenAIResponse:
    def test_parse_success(self):
        data = {
            "choices": [{"message": {"content": "Hello back!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        content, inp, out = _parse_openai_response(data)
        assert content == "Hello back!"
        assert inp == 10
        assert out == 20


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

class TestCalculateCost:
    def test_known_model(self):
        cost = _calculate_cost("claude-sonnet-4-20250514", 1000, 500)
        expected = 1000 * (3.0 / 1_000_000) + 500 * (15.0 / 1_000_000)
        assert abs(cost - expected) < 0.0001

    def test_unknown_model(self):
        cost = _calculate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = _calculate_cost("gpt-4o-mini", 0, 0)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# Task model mapping
# ---------------------------------------------------------------------------

class TestTaskModelMap:
    def test_all_tasks_have_entries(self):
        expected_tasks = ["scoring", "content_resume", "content_cl", "content_answers", "qa_check", "copilot", "company_intel"]
        for task in expected_tasks:
            assert task in TASK_MODEL_MAP
            assert "provider" in TASK_MODEL_MAP[task]
            assert "model" in TASK_MODEL_MAP[task]

    def test_cost_table_covers_default_models(self):
        for task, cfg in TASK_MODEL_MAP.items():
            model = cfg["model"]
            assert model in COST_TABLE, f"Model {model} for task {task} not in COST_TABLE"
