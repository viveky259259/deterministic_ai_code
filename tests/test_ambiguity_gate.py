"""Tests for AmbiguityGate."""

import pytest

from src.core.ambiguity_gate import AmbiguityGate
from src.core.contracts import (
    AmbiguityBlock,
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
)


@pytest.fixture
def gate():
    return AmbiguityGate()


def _make_classification(confidence: Confidence) -> Classification:
    ni = NormalizedIntent("add", "Total", "test input", "freetext")
    return Classification(CanonicalType.PURE_FUNCTION, confidence, ni, "javascript")


class TestGateLogic:
    def test_high_confidence_passes(self, gate):
        c = _make_classification(Confidence.HIGH)
        result = gate.evaluate(c)
        assert isinstance(result, Classification)
        assert result is c

    def test_medium_confidence_halts(self, gate):
        c = _make_classification(Confidence.MEDIUM)
        result = gate.evaluate(c)
        assert isinstance(result, AmbiguityBlock)

    def test_low_confidence_halts(self, gate):
        c = _make_classification(Confidence.LOW)
        result = gate.evaluate(c)
        assert isinstance(result, AmbiguityBlock)


class TestAmbiguityBlockContent:
    def test_medium_has_question(self, gate):
        c = _make_classification(Confidence.MEDIUM)
        result = gate.evaluate(c)
        assert isinstance(result, AmbiguityBlock)
        assert len(result.clarifying_question) > 0

    def test_low_has_question(self, gate):
        c = _make_classification(Confidence.LOW)
        result = gate.evaluate(c)
        assert isinstance(result, AmbiguityBlock)
        assert len(result.clarifying_question) > 0

    def test_preserves_classification(self, gate):
        c = _make_classification(Confidence.MEDIUM)
        result = gate.evaluate(c)
        assert isinstance(result, AmbiguityBlock)
        assert result.classification is c

    def test_has_assumed_interpretation(self, gate):
        c = _make_classification(Confidence.LOW)
        result = gate.evaluate(c)
        assert isinstance(result, AmbiguityBlock)
        assert len(result.assumed_interpretation) > 0
