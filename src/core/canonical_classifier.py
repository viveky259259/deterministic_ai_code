"""L2 — Rule-based canonical intent classifier."""

from __future__ import annotations

from src.core.contracts import (
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
)

# Canonical verbs that indicate I/O (disqualify PURE_FUNCTION)
_IO_VERBS = frozenset({"save", "delete", "send", "fetch", "stream", "write", "update"})

# Keywords for each canonical type
_PREDICATE_KEYWORDS = frozenset({"is", "has", "can", "should"})
_AGGREGATOR_KEYWORDS = frozenset({"reduce", "sum", "count", "group", "filter", "aggregate"})
_CLASS_KEYWORDS = frozenset({"method", "on class", "inside", "member of", "member"})
_ASYNC_KEYWORDS = frozenset({"async", "await", "concurrent", "stream", "poll"})
_DATA_CONTRACT_KEYWORDS = frozenset({
    "type", "interface", "struct", "schema", "model",
    "entity", "record", "dto", "contract", "shape",
})

# Collection nouns that hint at AGGREGATOR
_COLLECTION_NOUNS = frozenset({
    "users", "items", "orders", "records", "entries", "elements",
    "events", "messages", "results", "values", "rows", "documents",
})

# Verbs that map to specific types
_PURE_VERBS = frozenset({
    "add", "subtract", "multiply", "divide", "calculate", "format",
})
_SIDE_EFFECT_VERBS = frozenset({"save", "delete", "send", "update", "write"})


class CanonicalClassifier:
    """Maps NormalizedIntent to CanonicalType with confidence level."""

    def classify(self, normalized: NormalizedIntent, language: str) -> Classification:
        """Classify normalized intent into canonical type."""
        matches = self._evaluate_rules(normalized)

        if len(matches) == 1:
            confidence = Confidence.HIGH
            intent_type = matches[0]
        elif len(matches) >= 2:
            confidence = Confidence.MEDIUM
            intent_type = matches[0]  # highest priority
        else:
            confidence = Confidence.LOW
            intent_type = CanonicalType.PURE_FUNCTION  # default fallback

        return Classification(
            intent_type=intent_type,
            confidence=confidence,
            normalized=normalized,
            language=language,
        )

    def _evaluate_rules(self, normalized: NormalizedIntent) -> list[CanonicalType]:
        """Return all matching CanonicalTypes, ordered by priority."""
        matches: list[CanonicalType] = []
        verb = normalized.canonical_verb
        raw = normalized.raw_input.lower()
        words = set(raw.split())

        # Priority 1: PURE_FUNCTION
        # Use canonical verb (not raw words) to check I/O disqualification
        if verb in _PURE_VERBS and verb not in _IO_VERBS:
            matches.append(CanonicalType.PURE_FUNCTION)

        # Priority 2: PREDICATE
        if words & _PREDICATE_KEYWORDS or verb == "validate":
            matches.append(CanonicalType.PREDICATE)

        # Priority 3: TRANSFORMER
        # Only match on canonical verb, not preposition "to" in raw text
        if verb == "transform":
            matches.append(CanonicalType.TRANSFORMER)

        # Priority 4: AGGREGATOR
        if (words & _COLLECTION_NOUNS and words & _AGGREGATOR_KEYWORDS) or (
            verb in ("add", "calculate") and words & _COLLECTION_NOUNS
        ):
            matches.append(CanonicalType.AGGREGATOR)

        # Priority 5: SIDE_EFFECT_OP
        if verb in _SIDE_EFFECT_VERBS:
            matches.append(CanonicalType.SIDE_EFFECT_OP)

        # Priority 6: CLASS_METHOD
        if any(kw in raw for kw in _CLASS_KEYWORDS):
            matches.append(CanonicalType.CLASS_METHOD)

        # Priority 7: ASYNC_OPERATION
        if verb == "fetch" or words & _ASYNC_KEYWORDS:
            matches.append(CanonicalType.ASYNC_OPERATION)

        # Priority 8: DATA_CONTRACT
        if verb == "define" or (
            words & _DATA_CONTRACT_KEYWORDS
            and verb not in (_PURE_VERBS | _SIDE_EFFECT_VERBS | {"fetch", "validate", "transform"})
        ):
            matches.append(CanonicalType.DATA_CONTRACT)

        return matches
