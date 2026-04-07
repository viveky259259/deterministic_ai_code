"""DeterministicCodeAgent — full pipeline orchestrator."""

from __future__ import annotations

import hashlib

from src.core.ambiguity_gate import AmbiguityGate
from src.core.canonical_classifier import CanonicalClassifier
from src.core.claude_api_adapter import ClaudeAPIAdapter
from src.core.contracts import (
    AmbiguityBlock,
    Classification,
    DeterministicResult,
)
from src.core.drift_detector import DriftDetector
from src.core.intent_normalizer import IntentNormalizer
from src.core.multi_intent_splitter import MultiIntentSplitter
from src.core.retry_orchestrator import RetryOrchestrator
from src.core.schema_parser import SchemaParser
from src.core.spec_validator import SpecValidator
from src.core.template_binder import TemplateBinder
from src.logging.structured_logger import get_logger
from src.observability.tracing import generate_trace_id, traced_span

logger = get_logger("core.agent")

LANGUAGE_ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "py": "python",
    "python": "python",
    "python3": "python",
    "go": "go",
    "golang": "go",
}


class DeterministicCodeAgent:
    """Full pipeline: normalize → classify → gate → bind → call → parse → drift."""

    def __init__(self, api_key: str) -> None:
        self._normalizer = IntentNormalizer()
        self._classifier = CanonicalClassifier()
        self._gate = AmbiguityGate()
        self._binder = TemplateBinder()
        self._api = ClaudeAPIAdapter(api_key=api_key)
        self._parser = SchemaParser()
        self._drift = DriftDetector()
        self._spec_validator = SpecValidator()
        self._splitter = MultiIntentSplitter()
        self._orchestrator = RetryOrchestrator(self._api, self._parser, self._drift)

    def generate(
        self,
        user_intent: str,
        language: str = "javascript",
        max_retries: int = 3,
    ) -> DeterministicResult:
        """Generate deterministic code from user intent."""
        trace_id = generate_trace_id()
        language = self._normalise_language(language)

        logger.info(
            "generation_start",
            trace_id=trace_id,
            raw_intent=user_intent[:200],
            language=language,
            prompt_hash=hashlib.sha256(user_intent.encode()).hexdigest()[:16],
        )

        with traced_span(trace_id, "normalize"):
            normalized = self._normalizer.normalize(user_intent, language)

        # Spec bypass path
        if normalized.source in ("yaml_spec", "json_spec"):
            with traced_span(trace_id, "spec_validate"):
                classification = self._spec_validator.validate(user_intent)
        else:
            with traced_span(trace_id, "classify"):
                classification = self._classifier.classify(normalized, language)

        # Ambiguity gate
        with traced_span(trace_id, "ambiguity_gate"):
            gate_result = self._gate.evaluate(classification)

        if isinstance(gate_result, AmbiguityBlock):
            logger.info(
                "ambiguity_halt",
                trace_id=trace_id,
                confidence=classification.confidence.value,
                unclear=gate_result.unclear_dimension,
            )
            return DeterministicResult(
                sections=None,
                content_hash="",
                raw_output="",
                is_ambiguity=True,
                ambiguity=gate_result,
            )

        # gate_result is Classification at this point
        classification = gate_result

        with traced_span(trace_id, "bind_template"):
            bound_prompt = self._binder.bind(classification)

        # Compute intent key for drift detection
        intent_key = self._drift.compute_intent_key(
            verb=classification.normalized.canonical_verb,
            noun=classification.normalized.canonical_noun,
            language=classification.language,
            intent_type=classification.intent_type.value,
        )

        with traced_span(trace_id, "execute_with_retry"):
            result = self._orchestrator.execute(
                bound_prompt=bound_prompt,
                intent_key=intent_key,
                max_retries=max_retries,
                trace_id=trace_id,
            )

        logger.info(
            "generation_complete",
            trace_id=trace_id,
            content_hash=result.content_hash,
            is_ambiguity=result.is_ambiguity,
        )
        return result

    def _normalise_language(self, lang: str) -> str:
        """Normalise language aliases to canonical names."""
        key = lang.lower().strip()
        if key not in LANGUAGE_ALIASES:
            raise ValueError(f"Unsupported language: {lang}")
        return LANGUAGE_ALIASES[key]

    def generate_multi(
        self,
        user_intent: str,
        language: str = "javascript",
        max_retries: int = 3,
    ) -> list[DeterministicResult]:
        """Split multi-intent input into N independent pipeline runs."""
        language = self._normalise_language(language)
        sub_intents = self._splitter.split(user_intent)

        results: list[DeterministicResult] = []
        for sub_intent in sub_intents:
            try:
                result = self.generate(sub_intent, language=language, max_retries=max_retries)
                results.append(result)
            except (ValueError, RuntimeError) as e:
                logger.warning("sub_intent_failed", sub_intent=sub_intent, error=str(e))
                # Sub-intent failure does not block subsequent sub-intents
                results.append(DeterministicResult(
                    sections=None,
                    content_hash="",
                    raw_output=str(e),
                    is_ambiguity=True,
                ))
        return results

    def reset_session(self) -> None:
        """Reset drift detector session map (for testing)."""
        self._drift.reset()
