"""L5 — Session-scoped hash comparison for determinism enforcement."""

from __future__ import annotations

import hashlib

from src.logging.structured_logger import get_logger

logger = get_logger("core.drift_detector")


class DriftDetector:
    """Compares content_hash per intent_key. Raises on mismatch."""

    def __init__(self) -> None:
        self._session_hashes: dict[str, str] = {}

    def check(self, intent_key: str, content_hash: str) -> None:
        """Compare hash against session map. Raises RuntimeError on drift."""
        if intent_key in self._session_hashes:
            expected = self._session_hashes[intent_key]
            if expected != content_hash:
                raise RuntimeError(
                    f"DETERMINISM_VIOLATION\n"
                    f"  intent_key: {intent_key}\n"
                    f"  expected:   {expected}\n"
                    f"  received:   {content_hash}\n"
                    f"  Investigate before re-running."
                )
            logger.info("drift_check_passed", intent_key=intent_key)
        else:
            self._session_hashes[intent_key] = content_hash
            logger.info("drift_hash_stored", intent_key=intent_key, content_hash=content_hash)

    @staticmethod
    def compute_intent_key(
        verb: str, noun: str, language: str, intent_type: str
    ) -> str:
        """Compute session map key from classification components."""
        raw = f"{verb}:{noun}:{language}:{intent_type}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def reset(self) -> None:
        """Clear the session map (for testing)."""
        self._session_hashes.clear()

    @property
    def session_hashes(self) -> dict[str, str]:
        """Read-only access to session map (for testing)."""
        return dict(self._session_hashes)
