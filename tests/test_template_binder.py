"""Tests for TemplateBinder."""

import pytest

from src.core.contracts import (
    BoundPrompt,
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
)
from src.core.template_binder import SYSTEM_PROMPT, TemplateBinder


@pytest.fixture
def binder():
    return TemplateBinder()


def _make_classification(
    verb: str, noun: str, intent_type: CanonicalType, language: str = "javascript"
) -> Classification:
    ni = NormalizedIntent(verb, noun, f"test {verb} {noun}", "freetext")
    return Classification(intent_type, Confidence.HIGH, ni, language)


class TestFunctionNaming:
    def test_pure_function_noun_only(self, binder):
        c = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        bp = binder.bind(c)
        assert "Function name: total" in bp.user_message

    def test_predicate_is_prefix(self, binder):
        c = _make_classification("validate", "EvenNumber", CanonicalType.PREDICATE)
        bp = binder.bind(c)
        assert "Function name: isEvenNumber" in bp.user_message

    def test_transformer_to_prefix(self, binder):
        c = _make_classification("transform", "UserDto", CanonicalType.TRANSFORMER)
        bp = binder.bind(c)
        assert "Function name: toUserDto" in bp.user_message

    def test_side_effect_verb_noun(self, binder):
        c = _make_classification("save", "User", CanonicalType.SIDE_EFFECT_OP)
        bp = binder.bind(c)
        assert "Function name: saveUser" in bp.user_message

    def test_data_contract_pascal_noun(self, binder):
        c = _make_classification("define", "User", CanonicalType.DATA_CONTRACT)
        bp = binder.bind(c)
        assert "Type name: User" in bp.user_message
        assert "Intent type: DATA_CONTRACT" in bp.user_message

    def test_data_contract_pascal_noun_python(self, binder):
        """DATA_CONTRACT keeps PascalCase even in Python (it's a class name)."""
        c = _make_classification("define", "AuthToken", CanonicalType.DATA_CONTRACT, "python")
        bp = binder.bind(c)
        assert "Type name: AuthToken" in bp.user_message


class TestPythonCasing:
    def test_python_snake_case(self, binder):
        c = _make_classification("save", "User", CanonicalType.SIDE_EFFECT_OP, "python")
        bp = binder.bind(c)
        assert "Function name: save_user" in bp.user_message

    def test_python_pure_function(self, binder):
        c = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION, "python")
        bp = binder.bind(c)
        assert "Function name: total" in bp.user_message


class TestBoundPromptStructure:
    def test_has_system_prompt(self, binder):
        c = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        bp = binder.bind(c)
        assert bp.system_prompt == SYSTEM_PROMPT

    def test_has_language_target(self, binder):
        c = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        bp = binder.bind(c)
        assert "Language target: javascript" in bp.user_message

    def test_has_intent_type(self, binder):
        c = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        bp = binder.bind(c)
        assert "Intent type: PURE_FUNCTION" in bp.user_message

    def test_preserves_classification(self, binder):
        c = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        bp = binder.bind(c)
        assert bp.classification is c


class TestDeterminism:
    def test_equivalent_inputs_same_output(self, binder):
        c1 = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        c2 = _make_classification("add", "Total", CanonicalType.PURE_FUNCTION)
        bp1 = binder.bind(c1)
        bp2 = binder.bind(c2)
        assert bp1.user_message == bp2.user_message
