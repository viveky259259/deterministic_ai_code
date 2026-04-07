"""Tests for DriftDetector."""

import pytest

from src.core.drift_detector import DriftDetector


@pytest.fixture
def detector():
    return DriftDetector()


class TestHashStorage:
    def test_first_occurrence_stores(self, detector):
        detector.check("key1", "hash_abc")
        assert detector.session_hashes["key1"] == "hash_abc"

    def test_same_hash_passes(self, detector):
        detector.check("key1", "hash_abc")
        detector.check("key1", "hash_abc")  # no error

    def test_different_hash_raises(self, detector):
        detector.check("key1", "hash_abc")
        with pytest.raises(RuntimeError, match="DETERMINISM_VIOLATION"):
            detector.check("key1", "hash_xyz")

    def test_different_keys_independent(self, detector):
        detector.check("key1", "hash_abc")
        detector.check("key2", "hash_xyz")  # different key, no error
        assert len(detector.session_hashes) == 2


class TestViolationMessage:
    def test_violation_contains_details(self, detector):
        detector.check("key1", "expected_hash")
        with pytest.raises(RuntimeError) as exc_info:
            detector.check("key1", "actual_hash")
        msg = str(exc_info.value)
        assert "intent_key: key1" in msg
        assert "expected:   expected_hash" in msg
        assert "received:   actual_hash" in msg
        assert "Investigate" in msg


class TestIntentKey:
    def test_intent_key_computation(self, detector):
        key = detector.compute_intent_key("add", "Total", "javascript", "PURE_FUNCTION")
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest

    def test_intent_key_deterministic(self, detector):
        k1 = detector.compute_intent_key("add", "Total", "javascript", "PURE_FUNCTION")
        k2 = detector.compute_intent_key("add", "Total", "javascript", "PURE_FUNCTION")
        assert k1 == k2

    def test_different_inputs_different_keys(self, detector):
        k1 = detector.compute_intent_key("add", "Total", "javascript", "PURE_FUNCTION")
        k2 = detector.compute_intent_key("add", "Total", "python", "PURE_FUNCTION")
        assert k1 != k2


class TestReset:
    def test_reset_clears_map(self, detector):
        detector.check("key1", "hash")
        detector.reset()
        assert detector.session_hashes == {}

    def test_after_reset_new_hash_accepted(self, detector):
        detector.check("key1", "old_hash")
        detector.reset()
        detector.check("key1", "new_hash")  # no error — fresh session
        assert detector.session_hashes["key1"] == "new_hash"
