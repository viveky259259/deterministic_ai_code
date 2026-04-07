---
paths: ["src/**/*.py", "tests/**/*.py"]
---

# Logging Standards

## LLM Call Logging
Every LLM call MUST log:
- `request`: model, messages (truncated if >1000 chars), temperature, max_tokens
- `response`: completion text (truncated), finish_reason, usage (prompt_tokens, completion_tokens)
- `metadata`: trace_id, span_id, latency_ms, timestamp_iso, caller_function

## User Prompt Logging
Every user prompt MUST log:
- `prompt_hash`: SHA-256 of the raw prompt (for dedup without storing PII)
- `session_id`: unique per conversation session
- `timestamp_iso`: when the prompt was received
- `token_count`: estimated token count of the prompt

## Log Format
Use structlog with JSON output. Example:
```python
import structlog
logger = structlog.get_logger()
logger.info("llm_call", model="claude-opus-4-6", latency_ms=1200, tokens_out=500)
```

## Never Log
- Raw API keys or tokens
- Full user PII (use hashes)
- Binary/image data (log metadata only)
