"""Tests for IntentNormalizer."""

import pytest

from src.core.intent_normalizer import IntentNormalizer


@pytest.fixture
def normalizer():
    return IntentNormalizer()


class TestSynonymCollapse:
    def test_add_from_write(self, normalizer):
        result = normalizer.normalize("write add function", "javascript")
        assert result.canonical_verb == "add"

    def test_add_from_sum(self, normalizer):
        result = normalizer.normalize("make a sum method", "javascript")
        assert result.canonical_verb == "add"

    def test_add_from_plus(self, normalizer):
        result = normalizer.normalize("plus two numbers together", "javascript")
        assert result.canonical_verb == "add"

    def test_fetch_from_retrieve(self, normalizer):
        result = normalizer.normalize("retrieve user data", "javascript")
        assert result.canonical_verb == "fetch"

    def test_save_from_persist(self, normalizer):
        result = normalizer.normalize("persist data to disk", "javascript")
        assert result.canonical_verb == "save"

    def test_validate_from_check(self, normalizer):
        result = normalizer.normalize("check if even number", "javascript")
        assert result.canonical_verb == "validate"

    def test_transform_from_convert(self, normalizer):
        result = normalizer.normalize("convert user to DTO", "javascript")
        assert result.canonical_verb == "transform"

    def test_calculate_from_compute(self, normalizer):
        result = normalizer.normalize("compute the total amount", "javascript")
        assert result.canonical_verb == "calculate"

    def test_define_from_define(self, normalizer):
        result = normalizer.normalize("define a User type", "typescript")
        assert result.canonical_verb == "define"

    def test_define_from_model(self, normalizer):
        result = normalizer.normalize("model a User entity", "python")
        assert result.canonical_verb == "define"

    def test_define_from_schema(self, normalizer):
        result = normalizer.normalize("schema for AuthToken", "typescript")
        assert result.canonical_verb == "define"

    def test_define_noun_extraction(self, normalizer):
        """'type', 'interface', 'struct' should be filtered as filler words."""
        result = normalizer.normalize("define a User type", "typescript")
        assert result.canonical_noun == "User"

    def test_define_noun_interface(self, normalizer):
        result = normalizer.normalize("define User interface", "typescript")
        assert result.canonical_noun == "User"

    def test_unknown_verb(self, normalizer):
        result = normalizer.normalize("frobnicate the data", "javascript")
        assert result.canonical_verb == "unknown"


class TestInputValidation:
    def test_empty_input_raises(self, normalizer):
        with pytest.raises(ValueError, match="Intent too short"):
            normalizer.normalize("", "javascript")

    def test_short_input_raises(self, normalizer):
        with pytest.raises(ValueError, match="Intent too short"):
            normalizer.normalize("ab", "javascript")

    def test_whitespace_only_raises(self, normalizer):
        with pytest.raises(ValueError, match="Intent too short"):
            normalizer.normalize("  ", "javascript")


class TestCaseInsensitive:
    def test_uppercase(self, normalizer):
        result = normalizer.normalize("CREATE A METHOD TO SUM TWO NUMBERS", "javascript")
        assert result.canonical_verb == "add"

    def test_mixed_case(self, normalizer):
        result = normalizer.normalize("Write Add Function", "javascript")
        assert result.canonical_verb == "add"


class TestYamlDetection:
    def test_yaml_spec_detected(self, normalizer):
        result = normalizer.normalize("intent: pure_function\nverb: add", "javascript")
        assert result.source == "yaml_spec"

    def test_freetext_source(self, normalizer):
        result = normalizer.normalize("write add function", "javascript")
        assert result.source == "freetext"


class TestWhitespaceHandling:
    def test_leading_trailing_whitespace(self, normalizer):
        result = normalizer.normalize("  write add function  ", "javascript")
        assert result.canonical_verb == "add"

    def test_preserves_raw_input(self, normalizer):
        raw = "  write add function  "
        result = normalizer.normalize(raw, "javascript")
        assert result.raw_input == raw
