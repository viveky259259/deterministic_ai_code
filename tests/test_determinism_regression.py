"""F-18 — Determinism regression suite.

Verifies that the pipeline produces identical content_hash values for:
  1. Equivalent phrasings (synonym collapse correctness)
  2. Repeated identical calls (idempotency)
  3. Cross-type coverage

These tests use a mocked Claude API to verify pipeline determinism
independent of model behavior. Real API regression tests (420 calls)
are run separately via CI.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.agent import DeterministicCodeAgent

# Canonical raw output templates per intent type
_RAW_OUTPUTS: dict[str, str] = {
    "define": """
---INTENT_CLASSIFICATION---
type: DATA_CONTRACT
confidence: HIGH
canonical_verb: define
canonical_noun: User

---SIGNATURE---
typescript: interface User { readonly id: string; readonly email: string; }

---IMPLEMENTATION---
```typescript
interface User {
  readonly id: string;
  readonly email: string;
}
```

---INVARIANTS---
preconditions:
  - all fields must be provided
postconditions:
  - object is immutable
edge_cases:
  - empty id is invalid

---TEST_ORACLE---
```typescript
const user: User = { id: '1', email: 'a@b.com' };
assert(user.id === '1');
assert(typeof user.email === 'string');
```
---
""",
    "add": """
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
""",
    "validate": """
---INTENT_CLASSIFICATION---
type: PREDICATE
confidence: HIGH
canonical_verb: validate
canonical_noun: EvenNumber

---SIGNATURE---
javascript: const isEvenNumber = (number) => number % 2 === 0

---IMPLEMENTATION---
```javascript
const isEvenNumber = (number) => number % 2 === 0;
```

---INVARIANTS---
preconditions:
  - number must be an integer
postconditions:
  - returns true if number is even
edge_cases:
  - isEvenNumber(0) => true

---TEST_ORACLE---
```javascript
assert(isEvenNumber(2) === true);
assert(isEvenNumber(3) === false);
assert(isEvenNumber(0) === true);
```
---
""",
}


def _mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=100, output_tokens=200)
    return response


@pytest.fixture
def mock_agent():
    """Agent with mocked API that returns canonical output for 'add'."""
    with patch("src.core.claude_api_adapter.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(_RAW_OUTPUTS["add"])
        mock_cls.return_value = mock_client
        agent = DeterministicCodeAgent(api_key="test-key")
        yield agent, mock_client


# ── Idempotency Tests ────────────────────────────────────────────────────────


class TestIdempotency:
    """Same intent must produce byte-for-byte identical output across runs."""

    def test_identical_hash_across_5_runs(self, mock_agent):
        agent, _ = mock_agent
        results = [agent.generate("write add function") for _ in range(5)]
        hashes = [r.content_hash for r in results]
        assert len(set(hashes)) == 1, f"Drift detected: {set(hashes)}"

    def test_identical_hash_across_10_runs(self, mock_agent):
        agent, _ = mock_agent
        results = [agent.generate("write add function") for _ in range(10)]
        hashes = [r.content_hash for r in results]
        assert len(set(hashes)) == 1, f"Drift detected: {set(hashes)}"


# ── Synonym Collapse Tests ───────────────────────────────────────────────────


class TestSynonymHashStability:
    """All synonym phrasings must resolve to the same canonical output."""

    @pytest.mark.parametrize("phrase", [
        "write add function",
        "create a sum function",
        "create a function to add two numbers",
        "I need a plus function",
        "combine two numbers",
    ])
    def test_add_synonyms_same_hash(self, phrase, mock_agent):
        agent, _ = mock_agent
        results = [agent.generate(phrase, "javascript") for _ in range(3)]
        hashes = [r.content_hash for r in results]
        assert len(set(hashes)) == 1, f"Synonym drift for '{phrase}': {set(hashes)}"

    def test_all_add_synonyms_same_hash(self, mock_agent):
        """All add synonyms must produce the same hash as each other."""
        agent, _ = mock_agent
        # Avoid "method" keyword which triggers CLASS_METHOD ambiguity
        phrases = [
            "write add function",
            "create a sum function",
            "I need a plus function",
            "combine two numbers",
        ]
        hashes = [agent.generate(p, "javascript").content_hash for p in phrases]
        assert len(set(hashes)) == 1, f"Cross-synonym drift: {set(hashes)}"


# ── Cross-Type Regression ────────────────────────────────────────────────────


class TestCrossTypeRegression:
    """Each canonical type must produce stable output."""

    def test_pure_function_stable(self, mock_agent):
        agent, _ = mock_agent
        r1 = agent.generate("write add function", "javascript")
        r2 = agent.generate("write add function", "javascript")
        assert r1.content_hash == r2.content_hash

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_predicate_stable(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(_RAW_OUTPUTS["validate"])
        mock_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        results = [agent.generate("check if even", "javascript") for _ in range(5)]
        hashes = [r.content_hash for r in results]
        assert len(set(hashes)) == 1, f"Predicate drift: {set(hashes)}"

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_data_contract_stable(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(_RAW_OUTPUTS["define"])
        mock_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        results = [agent.generate("define a User type", "typescript") for _ in range(5)]
        hashes = [r.content_hash for r in results]
        assert len(set(hashes)) == 1, f"Data contract drift: {set(hashes)}"


# ── Cross-Language Regression ────────────────────────────────────────────────


class TestCrossLanguageRegression:
    """Same intent in different languages should produce different hashes
    (different code) but each language should be internally stable."""

    def test_js_stable(self, mock_agent):
        agent, _ = mock_agent
        hashes = [agent.generate("write add function", "js").content_hash for _ in range(5)]
        assert len(set(hashes)) == 1

    def test_python_stable(self, mock_agent):
        agent, _ = mock_agent
        hashes = [agent.generate("write add function", "python").content_hash for _ in range(5)]
        assert len(set(hashes)) == 1


# ── Drift Detection Integration ─────────────────────────────────────────────


class TestDriftDetectionIntegration:
    """DriftDetector catches hash mismatch within a session."""

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_drift_violation_on_output_change(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        # First call: canonical output
        mock_client.messages.create.return_value = _mock_response(_RAW_OUTPUTS["add"])
        agent = DeterministicCodeAgent(api_key="test-key")
        agent.generate("write add function", "javascript")

        # Second call: different implementation for same intent
        different = _RAW_OUTPUTS["add"].replace(
            "const total = (firstNumber, secondNumber) => firstNumber + secondNumber;",
            "const total = (x, y) => x + y;",
        )
        mock_client.messages.create.return_value = _mock_response(different)

        with pytest.raises(RuntimeError, match="DETERMINISM_VIOLATION"):
            agent.generate("write add function", "javascript")

    @patch("src.core.claude_api_adapter.anthropic.Anthropic")
    def test_reset_allows_new_hash(self, mock_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(_RAW_OUTPUTS["add"])
        mock_cls.return_value = mock_client

        agent = DeterministicCodeAgent(api_key="test-key")
        agent.generate("write add function", "javascript")
        agent.reset_session()

        # After reset, even a different hash is accepted
        different = _RAW_OUTPUTS["add"].replace(
            "const total = (firstNumber, secondNumber) => firstNumber + secondNumber;",
            "const total = (x, y) => x + y;",
        )
        mock_client.messages.create.return_value = _mock_response(different)
        result = agent.generate("write add function", "javascript")
        assert not result.is_ambiguity
