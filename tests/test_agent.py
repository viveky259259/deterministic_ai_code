"""Tests for DeterministicCodeAgent — unit + integration with mocked API."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.agent import LANGUAGE_ALIASES, DeterministicCodeAgent
from src.core.contracts import (
    AmbiguityBlock,
    CanonicalType,
    Confidence,
    DeterministicResult,
    NormalizedIntent,
    ParsedSections,
)

# --- Valid raw output that SchemaParser can parse ---
VALID_RAW_OUTPUT = """
---INTENT_CLASSIFICATION---
type: PURE_FUNCTION
confidence: HIGH
canonical_verb: add
canonical_noun: Total

---SIGNATURE---
javascript: const total = (firstNumber, secondNumber) => firstNumber + secondNumber

---IMPLEMENTATION---
```javascript
const total = (firstNumber, secondNumber) => firstNumber + secondNumber;
```

---INVARIANTS---
preconditions:
  - firstNumber must be a finite number
postconditions:
  - returns the arithmetic sum
edge_cases:
  - (0, 0) => 0

---TEST_ORACLE---
```javascript
assert(total(1, 2) === 3);
assert(total(0, 0) === 0);
assert(total(-1, 1) === 0);
```
---
"""

DATA_CONTRACT_RAW_OUTPUT = """
---INTENT_CLASSIFICATION---
type: DATA_CONTRACT
confidence: HIGH
canonical_verb: define
canonical_noun: User

---SIGNATURE---
typescript: interface User { readonly id: string; readonly email: string; readonly createdAt: Date; }

---IMPLEMENTATION---
```typescript
interface User {
  readonly id: string;
  readonly email: string;
  readonly createdAt: Date;
}
```

---INVARIANTS---
preconditions:
  - all fields must be provided at construction
postconditions:
  - object is immutable after creation
edge_cases:
  - empty string for id or email is invalid
design_principles:
  - Single Responsibility: one data shape, no logic
  - Immutable by default via readonly

---TEST_ORACLE---
```typescript
const user: User = { id: '1', email: 'a@b.com', createdAt: new Date() };
assert(user.id === '1');
assert(typeof user.email === 'string');
assert(user.createdAt instanceof Date);
```
---
"""

AMBIGUITY_RAW_OUTPUT = """
---AMBIGUITY---
unclear_dimension: verb not recognised
clarifying_question: What type of function is this?
assumed_interpretation: PURE_FUNCTION
---
"""


def _mock_anthropic_response(text: str) -> MagicMock:
    """Build a mock Anthropic API response."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=100, output_tokens=200)
    return response


class TestLanguageNormalization:
    def test_js_alias(self):
        agent = DeterministicCodeAgent.__new__(DeterministicCodeAgent)
        assert agent._normalise_language("js") == "javascript"

    def test_py_alias(self):
        agent = DeterministicCodeAgent.__new__(DeterministicCodeAgent)
        assert agent._normalise_language("py") == "python"

    def test_golang_alias(self):
        agent = DeterministicCodeAgent.__new__(DeterministicCodeAgent)
        assert agent._normalise_language("golang") == "go"

    def test_python3_alias(self):
        agent = DeterministicCodeAgent.__new__(DeterministicCodeAgent)
        assert agent._normalise_language("python3") == "python"

    def test_unsupported_language_raises(self):
        agent = DeterministicCodeAgent.__new__(DeterministicCodeAgent)
        with pytest.raises(ValueError, match="Unsupported language: rust"):
            agent._normalise_language("rust")

    def test_case_insensitive(self):
        agent = DeterministicCodeAgent.__new__(DeterministicCodeAgent)
        assert agent._normalise_language("JavaScript") == "javascript"
        assert agent._normalise_language("PYTHON") == "python"


class TestLanguageAliases:
    def test_all_aliases_present(self):
        assert "js" in LANGUAGE_ALIASES
        assert "ts" in LANGUAGE_ALIASES
        assert "py" in LANGUAGE_ALIASES
        assert "go" in LANGUAGE_ALIASES
        assert "golang" in LANGUAGE_ALIASES
        assert "python3" in LANGUAGE_ALIASES

    def test_canonical_names_present(self):
        assert "javascript" in LANGUAGE_ALIASES
        assert "typescript" in LANGUAGE_ALIASES
        assert "python" in LANGUAGE_ALIASES
        assert "go" in LANGUAGE_ALIASES


class TestHappyPath:
    """Full pipeline with mocked Claude API."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_generate_add_function(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("write add function", language="javascript")

        assert not result.is_ambiguity
        assert result.sections is not None
        assert "const total" in result.sections.implementation
        assert len(result.content_hash) == 16

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_generate_returns_deterministic_hash(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        r1 = agent.generate("write add function", language="javascript")
        r2 = agent.generate("write add function", language="javascript")
        assert r1.content_hash == r2.content_hash

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_generate_with_python(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("write add function", language="py")

        assert not result.is_ambiguity
        assert result.sections is not None


class TestDataContract:
    """DATA_CONTRACT type through the full pipeline."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_define_user_type(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(
            DATA_CONTRACT_RAW_OUTPUT
        )
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("define a User type", language="typescript")

        assert not result.is_ambiguity
        assert result.sections is not None
        assert "interface User" in result.sections.implementation
        assert len(result.content_hash) == 16

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_data_contract_deterministic(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(
            DATA_CONTRACT_RAW_OUTPUT
        )
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        r1 = agent.generate("define a User type", language="typescript")
        r2 = agent.generate("define a User type", language="typescript")
        assert r1.content_hash == r2.content_hash

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_schema_synonym_routes_to_data_contract(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(
            DATA_CONTRACT_RAW_OUTPUT
        )
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("schema for User", language="typescript")

        assert not result.is_ambiguity
        assert result.sections is not None


class TestAmbiguityPath:
    """Pipeline halts on ambiguous input."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_unknown_verb_returns_ambiguity(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("frobnicate the data", language="javascript")

        assert result.is_ambiguity
        assert result.ambiguity is not None
        assert result.content_hash == ""
        # Should NOT have called the API
        mock_client.messages.create.assert_not_called()

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_ambiguity_block_has_question(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = MagicMock()

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("frobnicate the data", language="javascript")

        assert result.ambiguity is not None
        assert len(result.ambiguity.clarifying_question) > 0
        assert len(result.ambiguity.assumed_interpretation) > 0


class TestSpecBypass:
    """YAML/JSON spec input bypasses normalisation."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_yaml_spec_bypasses_normalizer(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        spec = """
intent: pure_function
verb: add
noun: Total
language: javascript
"""
        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate(spec, language="javascript")

        assert not result.is_ambiguity
        assert result.sections is not None


class TestDriftDetection:
    """Session-scoped hash comparison."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_drift_violation_raised(self, mock_anthropic_cls):
        """Different output for same intent within session raises."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # First call returns one implementation
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)

        agent = DeterministicCodeAgent(api_key="test-key")
        agent.generate("write add function", language="javascript")

        # Second call returns different implementation
        different_output = VALID_RAW_OUTPUT.replace(
            "const total = (firstNumber, secondNumber) => firstNumber + secondNumber;",
            "const total = (a, b) => a + b;",
        )
        mock_client.messages.create.return_value = _mock_anthropic_response(different_output)

        with pytest.raises(RuntimeError, match="DETERMINISM_VIOLATION"):
            agent.generate("write add function", language="javascript")

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_reset_session_clears_drift(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        agent.generate("write add function", language="javascript")
        agent.reset_session()

        # After reset, different hash should be accepted
        different_output = VALID_RAW_OUTPUT.replace(
            "const total = (firstNumber, secondNumber) => firstNumber + secondNumber;",
            "const total = (a, b) => a + b;",
        )
        mock_client.messages.create.return_value = _mock_anthropic_response(different_output)

        result = agent.generate("write add function", language="javascript")
        assert not result.is_ambiguity


class TestRetryPath:
    """Schema failure triggers retry."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_retry_on_bad_output(self, mock_anthropic_cls):
        mock_client = MagicMock()
        # First call returns garbage, second returns valid
        mock_client.messages.create.side_effect = [
            _mock_anthropic_response("invalid output"),
            _mock_anthropic_response(VALID_RAW_OUTPUT),
        ]
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("write add function", language="javascript")

        assert not result.is_ambiguity
        assert result.sections is not None
        assert mock_client.messages.create.call_count == 2

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_max_retries_raises(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response("bad output always")
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        with pytest.raises(ValueError, match="Schema validation failed after 3 attempts"):
            agent.generate("write add function", language="javascript")

        assert mock_client.messages.create.call_count == 3

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_ambiguity_in_api_response(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(AMBIGUITY_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        result = agent.generate("write add function", language="javascript")

        assert result.is_ambiguity


class TestMultiGenerate:
    """F-04: multi-function decomposition via generate_multi."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_multi_generate_splits(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        results = agent.generate_multi(
            "write add and subtract functions", language="javascript"
        )
        assert len(results) >= 2

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_single_intent_returns_one(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(VALID_RAW_OUTPUT)
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        results = agent.generate_multi("write add function", language="javascript")
        assert len(results) == 1
        assert not results[0].is_ambiguity

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_sub_intent_failure_does_not_block(self, mock_anthropic_cls):
        mock_client = MagicMock()
        # First sub-intent fails (always bad output), second succeeds
        mock_client.messages.create.side_effect = [
            _mock_anthropic_response("bad"),
            _mock_anthropic_response("bad"),
            _mock_anthropic_response("bad"),
            _mock_anthropic_response(VALID_RAW_OUTPUT),
        ]
        mock_anthropic_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        results = agent.generate_multi(
            "write add and subtract functions", language="javascript"
        )
        assert len(results) == 2
        # First failed (ambiguity fallback), second succeeded
        assert results[0].is_ambiguity  # failure wrapped
        assert not results[1].is_ambiguity


class TestInputValidation:
    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_empty_intent_raises(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = MagicMock()
        agent = DeterministicCodeAgent(api_key="test-key")
        with pytest.raises(ValueError, match="Intent too short"):
            agent.generate("", language="javascript")

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_unsupported_language_raises(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = MagicMock()
        agent = DeterministicCodeAgent(api_key="test-key")
        with pytest.raises(ValueError, match="Unsupported language"):
            agent.generate("write add function", language="brainfuck")
