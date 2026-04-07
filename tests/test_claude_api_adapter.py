"""Tests for ClaudeAPIAdapter — config validation + mocked API calls."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.claude_api_adapter import MODEL, TEMPERATURE, ClaudeAPIAdapter
from src.core.contracts import (
    BoundPrompt,
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
)


class TestLockedConfig:
    def test_temperature_is_zero(self):
        assert TEMPERATURE == 0

    def test_model_is_pinned(self):
        assert MODEL == "claude-sonnet-4-20250514"

    def test_model_not_latest(self):
        assert "latest" not in MODEL

    def test_model_not_preview(self):
        assert "preview" not in MODEL

    def test_model_has_version(self):
        assert "2025" in MODEL


def _make_bound_prompt() -> BoundPrompt:
    ni = NormalizedIntent("add", "Total", "test", "freetext")
    c = Classification(CanonicalType.PURE_FUNCTION, Confidence.HIGH, ni, "javascript")
    return BoundPrompt("system prompt", "user message", c)


def _mock_response(text: str = "response text") -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=50, output_tokens=100)
    return response


class TestAdapterConstruction:
    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_creates_client(self, mock_cls):
        adapter = ClaudeAPIAdapter(api_key="test-key")
        mock_cls.assert_called_once_with(api_key="test-key")


class TestCall:
    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_call_returns_string(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response("hello world")
        mock_cls.return_value = mock_client

        adapter = ClaudeAPIAdapter(api_key="test-key")
        result = adapter.call(_make_bound_prompt())

        assert result == "hello world"
        assert isinstance(result, str)

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_call_uses_locked_config(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response()
        mock_cls.return_value = mock_client

        adapter = ClaudeAPIAdapter(api_key="test-key")
        adapter.call(_make_bound_prompt())

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == MODEL
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 2048

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_call_passes_system_prompt(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response()
        mock_cls.return_value = mock_client

        adapter = ClaudeAPIAdapter(api_key="test-key")
        bp = _make_bound_prompt()
        adapter.call(bp)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "system prompt"

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_call_passes_user_message(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response()
        mock_cls.return_value = mock_client

        adapter = ClaudeAPIAdapter(api_key="test-key")
        bp = _make_bound_prompt()
        adapter.call(bp)

        call_kwargs = mock_client.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "user message"

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_call_with_trace_and_attempt(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response()
        mock_cls.return_value = mock_client

        adapter = ClaudeAPIAdapter(api_key="test-key")
        result = adapter.call(_make_bound_prompt(), trace_id="trace123", attempt=2)

        assert isinstance(result, str)
