"""L1 — Intent normalizer. Synonym collapse + verb/noun extraction."""

from __future__ import annotations

import re
import unicodedata

from src.core.contracts import NormalizedIntent

VERB_SYNONYM_TABLE: dict[str, list[str]] = {
    "add": ["add", "sum", "plus", "combine"],
    "subtract": ["subtract", "minus", "remove from"],
    "multiply": ["multiply", "times", "product"],
    "divide": ["divide", "split by", "quotient"],
    "format": ["format", "render", "display", "show"],
    "fetch": ["fetch", "get", "retrieve", "pull"],
    "validate": ["validate", "check", "verify", "ensure"],
    "transform": ["transform", "convert", "map", "cast"],
    "calculate": ["calculate", "compute", "derive"],
    "save": ["save", "persist", "store", "write"],
    "define": ["define", "model", "schema", "shape", "contract"],
}

# Reverse lookup: synonym → canonical verb
_SYNONYM_LOOKUP: dict[str, str] = {}
for _canonical, _synonyms in VERB_SYNONYM_TABLE.items():
    for _syn in _synonyms:
        _SYNONYM_LOOKUP[_syn] = _canonical

# Default noun mapping for common canonical verbs
_DEFAULT_NOUNS: dict[str, str] = {
    "add": "Total",
    "subtract": "Difference",
    "multiply": "Product",
    "divide": "Quotient",
    "format": "Output",
    "fetch": "Data",
    "validate": "Input",
    "transform": "Output",
    "calculate": "Result",
    "save": "Record",
    "define": "Entity",
}

_YAML_INDICATORS = ("intent:", "verb:", "noun:", "---")


class IntentNormalizer:
    """Collapses user input into canonical verb+noun via synonym table."""

    def normalize(self, raw_input: str, language: str) -> NormalizedIntent:
        """Normalize raw user input to canonical form."""
        text = raw_input.strip()
        text = unicodedata.normalize("NFKC", text)

        if len(text) < 3:
            raise ValueError("Intent too short")

        if self._detect_yaml_spec(text):
            return NormalizedIntent(
                canonical_verb="",
                canonical_noun="",
                raw_input=raw_input,
                source="yaml_spec",
            )

        lowered = text.lower()
        verb = self._extract_verb(lowered)
        noun = self._extract_noun(lowered, verb)

        return NormalizedIntent(
            canonical_verb=verb or "unknown",
            canonical_noun=noun,
            raw_input=raw_input,
            source="freetext",
        )

    def _extract_verb(self, text: str) -> str | None:
        """Find canonical verb by matching against synonym table."""
        # Try multi-word synonyms first (e.g. "remove from", "split by")
        for canonical, synonyms in VERB_SYNONYM_TABLE.items():
            for syn in sorted(synonyms, key=len, reverse=True):
                if syn in text:
                    return canonical
        return None

    def _extract_noun(self, text: str, verb: str | None) -> str:
        """Derive PascalCase noun from remaining text after verb extraction."""
        if verb and verb in _DEFAULT_NOUNS:
            # Check for explicit nouns in the text
            noun = self._find_explicit_noun(text, verb)
            if noun:
                return noun
            return _DEFAULT_NOUNS[verb]
        return self._find_explicit_noun(text, verb) or "Unknown"

    def _find_explicit_noun(self, text: str, verb: str | None) -> str | None:
        """Try to extract an explicit noun from the text."""
        # Remove common filler words
        filler = {
            "write", "create", "make", "build", "a", "an", "the", "function",
            "method", "that", "to", "two", "numbers", "me", "i", "need",
            "type", "interface", "struct", "class", "for", "with", "new",
        }
        if verb:
            # Also remove all synonyms for the matched verb
            for syn in VERB_SYNONYM_TABLE.get(verb, []):
                filler.add(syn)

        words = re.findall(r"[a-z]+", text)
        nouns = [w for w in words if w not in filler and len(w) > 2]

        if nouns:
            # PascalCase the first meaningful noun
            return nouns[0].capitalize()
        return None

    def _detect_yaml_spec(self, text: str) -> bool:
        """Check if input contains YAML spec structure."""
        lowered = text.lower()
        return any(indicator in lowered for indicator in _YAML_INDICATORS)
