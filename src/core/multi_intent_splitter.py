"""F-04 — Multi-function decomposition. Splits multi-intent requests."""

from __future__ import annotations

import re

from src.logging.structured_logger import get_logger

logger = get_logger("core.multi_intent_splitter")

# Patterns that indicate multiple intents
_SPLIT_CONJUNCTIONS = re.compile(
    r"\band\b(?:\s+also\b)?",
    re.IGNORECASE,
)

# Phrases that look compound but are single intents
_SINGLE_INTENT_PHRASES = frozenset({
    "calculator", "crud", "api", "module", "class",
    "service", "handler", "controller", "manager",
})


class MultiIntentSplitter:
    """Splits multi-intent requests into independent sub-intents."""

    def split(self, raw_input: str) -> list[str]:
        """Split a raw intent into sub-intents. Returns list of 1+ strings."""
        text = raw_input.strip()
        lowered = text.lower()

        # Don't decompose if it looks like a single compound concept
        if any(phrase in lowered for phrase in _SINGLE_INTENT_PHRASES):
            return [text]

        # Check for explicit list patterns: "1. add 2. subtract"
        numbered = re.findall(r"\d+\.\s*(.+?)(?=\d+\.|$)", text)
        if len(numbered) >= 2:
            logger.info("split_numbered_list", count=len(numbered))
            return [item.strip() for item in numbered if item.strip()]

        # Check for comma-separated operations with verb phrases
        if "," in text and self._has_multiple_verbs(text):
            parts = [p.strip() for p in text.split(",") if p.strip()]
            if len(parts) >= 2:
                logger.info("split_comma_separated", count=len(parts))
                return parts

        # Check for "and" conjunction between verb phrases
        parts = _SPLIT_CONJUNCTIONS.split(text)
        if len(parts) >= 2 and self._has_multiple_verbs(text):
            cleaned = [p.strip() for p in parts if p.strip()]
            if len(cleaned) >= 2:
                logger.info("split_conjunction", count=len(cleaned))
                return cleaned

        return [text]

    def _has_multiple_verbs(self, text: str) -> bool:
        """Check if text contains multiple action verb phrases."""
        from src.core.intent_normalizer import VERB_SYNONYM_TABLE

        all_synonyms = set()
        for synonyms in VERB_SYNONYM_TABLE.values():
            all_synonyms.update(synonyms)

        # Also include common intent verbs not in synonym table
        all_synonyms.update({"write", "create", "make", "build", "implement"})

        lowered = text.lower()
        verb_count = sum(1 for syn in all_synonyms if f" {syn} " in f" {lowered} ")
        return verb_count >= 2
