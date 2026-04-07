"""Tests for SchemaParser."""

import pytest

from src.core.schema_parser import SchemaParser


@pytest.fixture
def parser():
    return SchemaParser()


VALID_OUTPUT = """
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
  - returns a number equal to the arithmetic sum
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


class TestValidParsing:
    def test_parses_valid_output(self, parser):
        result = parser.parse(VALID_OUTPUT)
        assert result is not None
        assert "PURE_FUNCTION" in result.intent_classification
        assert "const total" in result.implementation
        assert result.dependencies is None

    def test_fences_stripped(self, parser):
        result = parser.parse(VALID_OUTPUT)
        assert result is not None
        assert "```" not in result.implementation

    def test_implementation_content(self, parser):
        result = parser.parse(VALID_OUTPUT)
        assert result is not None
        assert result.implementation.startswith("const total")


class TestParseFailures:
    def test_missing_section_returns_none(self, parser):
        incomplete = """
---INTENT_CLASSIFICATION---
type: PURE_FUNCTION

---SIGNATURE---
javascript: const total = ...

---IMPLEMENTATION---
```javascript
const total = (a, b) => a + b;
```
"""
        result = parser.parse(incomplete)
        assert result is None

    def test_no_sections_returns_none(self, parser):
        result = parser.parse("just some random text")
        assert result is None

    def test_no_fence_returns_none(self, parser):
        bad = VALID_OUTPUT.replace("```javascript\n", "").replace("```\n", "")
        result = parser.parse(bad)
        assert result is None

    def test_import_in_implementation_returns_none(self, parser):
        bad = VALID_OUTPUT.replace(
            "const total = (firstNumber, secondNumber) => firstNumber + secondNumber;",
            "import math\nconst total = (a, b) => a + b;",
        )
        result = parser.parse(bad)
        assert result is None


class TestAmbiguityDetection:
    def test_ambiguity_detected(self, parser):
        output = """
---AMBIGUITY---
unclear_dimension: verb not recognised
clarifying_question: Is this a pure function?
assumed_interpretation: PURE_FUNCTION
---
"""
        assert parser.is_ambiguity(output)
        result = parser.parse(output)
        assert result is None

    def test_normal_output_not_ambiguity(self, parser):
        assert not parser.is_ambiguity(VALID_OUTPUT)
