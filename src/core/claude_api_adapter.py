"""L4 — Claude API adapter with locked configuration."""

from __future__ import annotations

import hashlib
import time

import anthropic

from src.core.contracts import BoundPrompt
from src.logging.structured_logger import get_logger
from src.observability.tracing import generate_span_id

logger = get_logger("core.claude_api_adapter")

MODEL = "claude-sonnet-4-20250514"
TEMPERATURE = 0
MAX_TOKENS = 2048


class ClaudeAPIAdapter:
    """Calls Claude API with locked config. temperature=0, model pinned."""

    def __init__(self, api_key: str) -> None:
        assert TEMPERATURE == 0, "Temperature must be 0 for determinism"
        assert "latest" not in MODEL, "Model must be pinned, not 'latest'"
        assert "preview" not in MODEL, "Model must be pinned, not 'preview'"

        self._client = anthropic.Anthropic(api_key=api_key)

    def call(
        self,
        bound_prompt: BoundPrompt,
        trace_id: str = "",
        attempt: int = 1,
    ) -> str:
        """Make a single Claude API call and return raw text."""
        span_id = generate_span_id()
        system_hash = hashlib.sha256(
            bound_prompt.system_prompt.encode("utf-8")
        ).hexdigest()[:16]

        logger.info(
            "llm_call_start",
            trace_id=trace_id,
            span_id=span_id,
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            system_prompt_hash=system_hash,
            user_prompt=bound_prompt.user_message[:200],
            attempt=attempt,
        )

        start = time.monotonic()
        response = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=bound_prompt.system_prompt,
            messages=[{"role": "user", "content": bound_prompt.user_message}],
        )
        latency_ms = (time.monotonic() - start) * 1000

        raw = response.content[0].text
        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

        logger.info(
            "llm_call_complete",
            trace_id=trace_id,
            span_id=span_id,
            content_hash=content_hash,
            finish_reason=response.stop_reason,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            latency_ms=round(latency_ms, 2),
            attempt=attempt,
        )

        return raw
