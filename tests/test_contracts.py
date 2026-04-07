"""Tests for data contracts."""

import pytest

from src.core.contracts import (
    AmbiguityBlock,
    BoundPrompt,
    CanonicalType,
    Classification,
    Confidence,
    DeterministicResult,
    NormalizedIntent,
    ParsedSections,
)


class TestCanonicalType:
    def test_all_types_present(self):
        assert len(CanonicalType) == 8

    def test_values_are_strings(self):
        assert all(isinstance(t.value, str) for t in CanonicalType)

    def test_value_matches_name(self):
        assert all(t.value == t.name for t in CanonicalType)

    def test_specific_types_exist(self):
        assert CanonicalType.PURE_FUNCTION.value == "PURE_FUNCTION"
        assert CanonicalType.PREDICATE.value == "PREDICATE"
        assert CanonicalType.ASYNC_OPERATION.value == "ASYNC_OPERATION"
        assert CanonicalType.DATA_CONTRACT.value == "DATA_CONTRACT"


class TestConfidence:
    def test_all_levels_present(self):
        assert len(Confidence) == 3

    def test_high_value(self):
        assert Confidence.HIGH.value == "HIGH"


class TestNormalizedIntent:
    def test_valid_freetext(self):
        ni = NormalizedIntent("add", "Total", "write add function", "freetext")
        assert ni.canonical_verb == "add"
        assert ni.source == "freetext"

    def test_valid_spec_source(self):
        ni = NormalizedIntent("add", "Total", "spec input", "yaml_spec")
        assert ni.source == "yaml_spec"

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError, match="Invalid source"):
            NormalizedIntent("add", "Total", "test", "invalid")

    def test_frozen(self):
        ni = NormalizedIntent("add", "Total", "test", "freetext")
        with pytest.raises(AttributeError):
            ni.canonical_verb = "subtract"  # type: ignore[misc]


class TestClassification:
    def _make_normalized(self):
        return NormalizedIntent("add", "Total", "test", "freetext")

    def test_valid_classification(self):
        c = Classification(
            CanonicalType.PURE_FUNCTION, Confidence.HIGH, self._make_normalized(), "javascript"
        )
        assert c.intent_type == CanonicalType.PURE_FUNCTION
        assert c.language == "javascript"

    def test_invalid_language_raises(self):
        with pytest.raises(ValueError, match="Invalid language"):
            Classification(
                CanonicalType.PURE_FUNCTION, Confidence.HIGH, self._make_normalized(), "rust"
            )


class TestAmbiguityBlock:
    def test_creation(self):
        ni = NormalizedIntent("unknown", "Thing", "frobnicate", "freetext")
        c = Classification(CanonicalType.PURE_FUNCTION, Confidence.LOW, ni, "javascript")
        ab = AmbiguityBlock("unclear verb", "Is this a function?", "Assuming PURE_FUNCTION", c)
        assert ab.unclear_dimension == "unclear verb"
        assert ab.classification.confidence == Confidence.LOW


class TestBoundPrompt:
    def test_creation(self):
        ni = NormalizedIntent("add", "Total", "test", "freetext")
        c = Classification(CanonicalType.PURE_FUNCTION, Confidence.HIGH, ni, "javascript")
        bp = BoundPrompt("system", "user msg", c)
        assert bp.system_prompt == "system"
        assert bp.user_message == "user msg"


class TestParsedSections:
    def test_all_fields(self):
        ps = ParsedSections(
            intent_classification="type: PURE_FUNCTION",
            signature="js: const total = ...",
            implementation="const total = (a, b) => a + b;",
            invariants="preconditions: ...",
            test_oracle="assert(total(1,2) === 3);",
        )
        assert ps.dependencies is None
        assert ps.implementation.startswith("const")

    def test_with_dependencies(self):
        ps = ParsedSections("ic", "sig", "impl", "inv", "test", dependencies="lodash")
        assert ps.dependencies == "lodash"


class TestDeterministicResult:
    def test_successful_result(self):
        ps = ParsedSections("ic", "sig", "impl", "inv", "test")
        dr = DeterministicResult(sections=ps, content_hash="abcdef1234567890", raw_output="raw")
        assert not dr.is_ambiguity
        assert len(dr.content_hash) == 16

    def test_ambiguity_result(self):
        dr = DeterministicResult(
            sections=None, content_hash="", raw_output="", is_ambiguity=True
        )
        assert dr.is_ambiguity

    def test_missing_sections_raises(self):
        with pytest.raises(ValueError, match="sections must be set"):
            DeterministicResult(sections=None, content_hash="abc", raw_output="")

    def test_nonempty_hash_on_ambiguity_raises(self):
        with pytest.raises(ValueError, match="content_hash must be empty"):
            DeterministicResult(
                sections=None, content_hash="abc", raw_output="", is_ambiguity=True
            )

    def test_compute_hash(self):
        h = DeterministicResult.compute_hash("const total = (a, b) => a + b;")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_compute_hash_deterministic(self):
        code = "const total = (firstNumber, secondNumber) => firstNumber + secondNumber;"
        assert DeterministicResult.compute_hash(code) == DeterministicResult.compute_hash(code)
