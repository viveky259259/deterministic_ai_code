"""Tests for MultiIntentSplitter."""

import pytest

from src.core.multi_intent_splitter import MultiIntentSplitter


@pytest.fixture
def splitter():
    return MultiIntentSplitter()


class TestSingleIntents:
    def test_simple_intent_not_split(self, splitter):
        result = splitter.split("write add function")
        assert result == ["write add function"]

    def test_calculator_not_decomposed(self, splitter):
        result = splitter.split("make a calculator")
        assert len(result) == 1

    def test_crud_not_decomposed(self, splitter):
        result = splitter.split("build a crud module")
        assert len(result) == 1

    def test_single_verb_not_split(self, splitter):
        result = splitter.split("check if even number")
        assert len(result) == 1


class TestConjunctionSplitting:
    def test_add_and_subtract(self, splitter):
        result = splitter.split("write add and subtract functions")
        assert len(result) == 2

    def test_create_and_validate(self, splitter):
        result = splitter.split("create add function and validate input")
        assert len(result) == 2


class TestCommaSplitting:
    def test_comma_separated_verbs(self, splitter):
        result = splitter.split("write add function, create subtract function")
        assert len(result) == 2


class TestNumberedList:
    def test_numbered_intents(self, splitter):
        result = splitter.split("1. add two numbers 2. check if even")
        assert len(result) == 2
        assert "add two numbers" in result[0]
        assert "check if even" in result[1]


class TestEdgeCases:
    def test_empty_after_strip(self, splitter):
        result = splitter.split("write add function")
        assert len(result) >= 1

    def test_preserves_text(self, splitter):
        result = splitter.split("write add function")
        assert result[0] == "write add function"
