"""Data contracts for the DetermBot pipeline.

All typed data structures that flow between pipeline stages.
Enums, dataclasses, and type aliases — no business logic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CanonicalType(Enum):
    """Supported canonical intent types. Classification is the first step."""

    PURE_FUNCTION = "PURE_FUNCTION"
    PREDICATE = "PREDICATE"
    TRANSFORMER = "TRANSFORMER"
    AGGREGATOR = "AGGREGATOR"
    SIDE_EFFECT_OP = "SIDE_EFFECT_OP"
    CLASS_METHOD = "CLASS_METHOD"
    ASYNC_OPERATION = "ASYNC_OPERATION"
    DATA_CONTRACT = "DATA_CONTRACT"


class Confidence(Enum):
    """Classification confidence. Only HIGH proceeds past AmbiguityGate."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class NormalizedIntent:
    """Output of IntentNormalizer — canonical verb+noun from synonym collapse."""

    canonical_verb: str
    canonical_noun: str
    raw_input: str
    source: str  # "freetext" | "yaml_spec" | "json_spec"

    def __post_init__(self) -> None:
        if self.source not in ("freetext", "yaml_spec", "json_spec"):
            raise ValueError(f"Invalid source: {self.source}")


@dataclass(frozen=True)
class Classification:
    """Output of CanonicalClassifier — type + confidence + language."""

    intent_type: CanonicalType
    confidence: Confidence
    normalized: NormalizedIntent
    language: str  # "javascript" | "typescript" | "python" | "go"

    def __post_init__(self) -> None:
        valid_languages = ("javascript", "typescript", "python", "go")
        if self.language not in valid_languages:
            raise ValueError(f"Invalid language: {self.language}")


@dataclass(frozen=True)
class AmbiguityBlock:
    """Returned when classification confidence < HIGH. Not an exception."""

    unclear_dimension: str
    clarifying_question: str
    assumed_interpretation: str
    classification: Classification


@dataclass(frozen=True)
class BoundPrompt:
    """Output of TemplateBinder — ready for Claude API call."""

    system_prompt: str
    user_message: str
    classification: Classification


@dataclass(frozen=True)
class ParsedSections:
    """Validated sections extracted from Claude API raw output."""

    intent_classification: str
    signature: str
    implementation: str
    invariants: str
    test_oracle: str
    dependencies: Optional[str] = None


@dataclass
class DeterministicResult:
    """Final pipeline output with content hash for drift detection."""

    sections: Optional[ParsedSections]
    content_hash: str
    raw_output: str
    is_ambiguity: bool = False
    ambiguity: Optional[AmbiguityBlock] = None

    def __post_init__(self) -> None:
        if not self.is_ambiguity and self.sections is None:
            raise ValueError("sections must be set when is_ambiguity is False")
        if self.is_ambiguity and self.content_hash != "":
            raise ValueError("content_hash must be empty when is_ambiguity is True")

    @staticmethod
    def compute_hash(implementation_code: str) -> str:
        """SHA-256[:16] of implementation code (fences stripped)."""
        return hashlib.sha256(implementation_code.encode("utf-8")).hexdigest()[:16]
