"""Tests for CanonicalClassifier."""

import pytest

from src.core.canonical_classifier import CanonicalClassifier
from src.core.contracts import CanonicalType, Confidence, NormalizedIntent


@pytest.fixture
def classifier():
    return CanonicalClassifier()


def _make_intent(verb: str, raw: str) -> NormalizedIntent:
    return NormalizedIntent(verb, "Test", raw, "freetext")


class TestClassificationRules:
    def test_pure_function_add(self, classifier):
        ni = _make_intent("add", "write add function")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.PURE_FUNCTION
        assert c.confidence == Confidence.HIGH

    def test_pure_function_calculate(self, classifier):
        ni = _make_intent("calculate", "calculate the total")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.PURE_FUNCTION
        assert c.confidence == Confidence.HIGH

    def test_predicate_validate(self, classifier):
        ni = _make_intent("validate", "check if even")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.PREDICATE
        assert c.confidence == Confidence.HIGH

    def test_predicate_is_keyword(self, classifier):
        ni = _make_intent("validate", "is it a valid email")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.PREDICATE

    def test_side_effect_save(self, classifier):
        ni = _make_intent("save", "save user to database")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.SIDE_EFFECT_OP
        assert c.confidence == Confidence.HIGH

    def test_async_fetch(self, classifier):
        ni = _make_intent("fetch", "fetch user profile")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.ASYNC_OPERATION
        assert c.confidence == Confidence.HIGH

    def test_transformer(self, classifier):
        ni = _make_intent("transform", "convert user to DTO")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.TRANSFORMER

    def test_data_contract_define_verb(self, classifier):
        ni = _make_intent("define", "define a User type")
        c = classifier.classify(ni, "typescript")
        assert c.intent_type == CanonicalType.DATA_CONTRACT
        assert c.confidence == Confidence.HIGH

    def test_data_contract_keywords(self, classifier):
        ni = _make_intent("unknown", "create a User interface")
        c = classifier.classify(ni, "typescript")
        assert c.intent_type == CanonicalType.DATA_CONTRACT

    def test_data_contract_not_triggered_by_pure_verb(self, classifier):
        """Pure function verbs should not trigger DATA_CONTRACT even with keywords."""
        ni = _make_intent("add", "add type values")
        c = classifier.classify(ni, "javascript")
        assert c.intent_type == CanonicalType.PURE_FUNCTION


class TestConfidenceLevels:
    def test_unknown_verb_low_confidence(self, classifier):
        ni = _make_intent("unknown", "frobnicate the data")
        c = classifier.classify(ni, "javascript")
        assert c.confidence == Confidence.LOW

    def test_single_match_high(self, classifier):
        ni = _make_intent("add", "write add function")
        c = classifier.classify(ni, "javascript")
        assert c.confidence == Confidence.HIGH


class TestLanguagePassthrough:
    def test_language_preserved(self, classifier):
        ni = _make_intent("add", "write add function")
        c = classifier.classify(ni, "python")
        assert c.language == "python"

    def test_normalized_preserved(self, classifier):
        ni = _make_intent("add", "write add function")
        c = classifier.classify(ni, "javascript")
        assert c.normalized is ni
