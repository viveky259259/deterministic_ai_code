"""Tests for RetryOrchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.contracts import (
    BoundPrompt,
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
    ParsedSections,
)
from src.core.drift_detector import DriftDetector
from src.core.retry_orchestrator import RETRY_SUFFIX, RetryOrchestrator
from src.core.schema_parser import SchemaParser


def _make_bound_prompt() -> BoundPrompt:
    ni = NormalizedIntent("add", "Total", "test", "freetext")
    c = Classification(CanonicalType.PURE_FUNCTION, Confidence.HIGH, ni, "javascript")
    return BoundPrompt("system", "user msg", c)


def _make_parsed_sections() -> ParsedSections:
    return ParsedSections(
        intent_classification="type: PURE_FUNCTION",
        signature="js: const total = ...",
        implementation="const total = (a, b) => a + b;",
        invariants="preconditions: ...",
        test_oracle="assert(true);",
    )


class TestSuccessPath:
    def test_success_on_first_attempt(self):
        api = MagicMock()
        api.call.return_value = "raw output"
        parser = MagicMock(spec=SchemaParser)
        parser.is_ambiguity.return_value = False
        parser.parse.return_value = _make_parsed_sections()
        drift = DriftDetector()

        orchestrator = RetryOrchestrator(api, parser, drift)
        result = orchestrator.execute(_make_bound_prompt(), "intent_key")

        assert result.sections is not None
        assert not result.is_ambiguity
        api.call.assert_called_once()


class TestRetryBehavior:
    def test_retry_on_schema_failure(self):
        api = MagicMock()
        api.call.return_value = "raw output"
        parser = MagicMock(spec=SchemaParser)
        parser.is_ambiguity.return_value = False
        parser.parse.side_effect = [None, _make_parsed_sections()]
        drift = DriftDetector()

        orchestrator = RetryOrchestrator(api, parser, drift)
        result = orchestrator.execute(_make_bound_prompt(), "intent_key")

        assert result.sections is not None
        assert api.call.call_count == 2

    def test_max_retries_exhausted(self):
        api = MagicMock()
        api.call.return_value = "raw output"
        parser = MagicMock(spec=SchemaParser)
        parser.is_ambiguity.return_value = False
        parser.parse.return_value = None  # always fails
        drift = DriftDetector()

        orchestrator = RetryOrchestrator(api, parser, drift)
        with pytest.raises(ValueError, match="Schema validation failed after 3 attempts"):
            orchestrator.execute(_make_bound_prompt(), "intent_key")

        assert api.call.call_count == 3

    def test_suffix_appended_on_retry(self):
        api = MagicMock()
        api.call.return_value = "raw output"
        parser = MagicMock(spec=SchemaParser)
        parser.is_ambiguity.return_value = False
        parser.parse.side_effect = [None, _make_parsed_sections()]
        drift = DriftDetector()

        orchestrator = RetryOrchestrator(api, parser, drift)
        orchestrator.execute(_make_bound_prompt(), "intent_key")

        # Second call should have suffix appended
        second_call = api.call.call_args_list[1]
        prompt = second_call[0][0]  # first positional arg
        assert RETRY_SUFFIX in prompt.user_message


class TestAmbiguityPath:
    def test_ambiguity_in_response(self):
        api = MagicMock()
        api.call.return_value = "---AMBIGUITY--- unclear"
        parser = MagicMock(spec=SchemaParser)
        parser.is_ambiguity.return_value = True
        drift = DriftDetector()

        orchestrator = RetryOrchestrator(api, parser, drift)
        result = orchestrator.execute(_make_bound_prompt(), "intent_key")

        assert result.is_ambiguity
        assert result.content_hash == ""
