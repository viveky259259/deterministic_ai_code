"""Bypass — Validates YAML/JSON spec input, skips synonym normalisation."""

from __future__ import annotations

import json
from typing import Any

import yaml

from src.core.contracts import (
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
)
from src.logging.structured_logger import get_logger

logger = get_logger("core.spec_validator")

_REQUIRED_FIELDS = ("intent", "verb", "noun", "language")

_INTENT_MAP: dict[str, CanonicalType] = {
    "pure_function": CanonicalType.PURE_FUNCTION,
    "predicate": CanonicalType.PREDICATE,
    "transformer": CanonicalType.TRANSFORMER,
    "aggregator": CanonicalType.AGGREGATOR,
    "side_effect_op": CanonicalType.SIDE_EFFECT_OP,
    "class_method": CanonicalType.CLASS_METHOD,
    "async_operation": CanonicalType.ASYNC_OPERATION,
    "data_contract": CanonicalType.DATA_CONTRACT,
}


class SchemaError(Exception):
    """Raised when a spec file has invalid structure."""


class SpecValidator:
    """Handles YAML/JSON spec input, bypassing normalisation."""

    def validate(self, spec_input: str) -> Classification:
        """Parse and validate spec, return Classification with confidence=HIGH."""
        parsed = self._parse(spec_input)
        self._validate_fields(parsed)

        intent_str = parsed["intent"].lower().strip()
        if intent_str not in _INTENT_MAP:
            raise SchemaError(f"Unknown intent type: {intent_str}")

        source = "json_spec" if self._is_json(spec_input) else "yaml_spec"
        normalized = NormalizedIntent(
            canonical_verb=parsed["verb"],
            canonical_noun=parsed["noun"],
            raw_input=spec_input,
            source=source,
        )

        language = parsed["language"].lower().strip()
        valid_languages = ("javascript", "typescript", "python", "go")
        if language not in valid_languages:
            raise SchemaError(f"Unsupported language: {language}")

        logger.info(
            "spec_validated",
            intent_type=intent_str,
            verb=parsed["verb"],
            noun=parsed["noun"],
            language=language,
        )

        return Classification(
            intent_type=_INTENT_MAP[intent_str],
            confidence=Confidence.HIGH,
            normalized=normalized,
            language=language,
        )

    def _parse(self, spec_input: str) -> dict[str, Any]:
        """Parse input as YAML or JSON."""
        text = spec_input.strip()
        if self._is_json(text):
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise SchemaError(f"Invalid spec format: {e}") from e
        try:
            result = yaml.safe_load(text)
            if not isinstance(result, dict):
                raise SchemaError("Invalid spec format: expected a mapping")
            return result
        except yaml.YAMLError as e:
            raise SchemaError(f"Invalid spec format: {e}") from e

    def _validate_fields(self, parsed: dict[str, Any]) -> None:
        """Validate all required fields are present."""
        for field in _REQUIRED_FIELDS:
            if field not in parsed:
                raise SchemaError(f"Missing required field: {field}")

    @staticmethod
    def _is_json(text: str) -> bool:
        """Detect whether input is JSON."""
        stripped = text.strip()
        return stripped.startswith("{") or stripped.startswith("[")
