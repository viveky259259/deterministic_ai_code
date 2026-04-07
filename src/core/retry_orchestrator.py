"""Ctrl — Retry loop on schema failures. Max 3 attempts."""

from __future__ import annotations

from src.core.claude_api_adapter import ClaudeAPIAdapter
from src.core.contracts import BoundPrompt, DeterministicResult, ParsedSections
from src.core.drift_detector import DriftDetector
from src.core.schema_parser import SchemaParser
from src.logging.structured_logger import get_logger

logger = get_logger("core.retry_orchestrator")

RETRY_SUFFIX = (
    "\n\nYour previous response did not conform to the required output schema. "
    "Reformat strictly. Every required section (INTENT_CLASSIFICATION, SIGNATURE, "
    "IMPLEMENTATION, INVARIANTS, TEST_ORACLE) must be present, delimited by ---, "
    "with no prose before or after. No alternatives. No explanations."
)


class RetryOrchestrator:
    """Executes API call with retry on schema failure."""

    def __init__(
        self,
        api_adapter: ClaudeAPIAdapter,
        schema_parser: SchemaParser,
        drift_detector: DriftDetector,
    ) -> None:
        self._api = api_adapter
        self._parser = schema_parser
        self._drift = drift_detector

    def execute(
        self,
        bound_prompt: BoundPrompt,
        intent_key: str,
        max_retries: int = 3,
        trace_id: str = "",
    ) -> DeterministicResult:
        """Execute API call with retry loop. Raises ValueError after max_retries."""
        current_message = bound_prompt.user_message

        for attempt in range(1, max_retries + 1):
            prompt = BoundPrompt(
                system_prompt=bound_prompt.system_prompt,
                user_message=current_message,
                classification=bound_prompt.classification,
            )

            raw = self._api.call(prompt, trace_id=trace_id, attempt=attempt)

            # Check for ambiguity in raw output
            if self._parser.is_ambiguity(raw):
                logger.info("ambiguity_in_response", attempt=attempt)
                return DeterministicResult(
                    sections=None,
                    content_hash="",
                    raw_output=raw,
                    is_ambiguity=True,
                )

            parsed = self._parser.parse(raw)

            if parsed is not None:
                content_hash = DeterministicResult.compute_hash(parsed.implementation)
                self._drift.check(intent_key, content_hash)

                logger.info(
                    "generation_success",
                    attempt=attempt,
                    content_hash=content_hash,
                    trace_id=trace_id,
                )
                return DeterministicResult(
                    sections=parsed,
                    content_hash=content_hash,
                    raw_output=raw,
                )

            logger.warning(
                "schema_validation_failed",
                attempt=attempt,
                max_retries=max_retries,
                trace_id=trace_id,
            )

            if attempt < max_retries:
                current_message += RETRY_SUFFIX

        raise ValueError(f"Schema validation failed after {max_retries} attempts")
