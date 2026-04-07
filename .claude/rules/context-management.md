---
paths: ["**/*"]
---

# Context Management Rules

## Compaction at 40%
- Monitor context window usage during long conversations
- When context reaches ~40% capacity, proactively compact by summarizing prior work
- Preserve: current task state, key decisions, file paths being edited, test results
- Discard: intermediate exploration, failed approaches already resolved, verbose tool output

## Sub-Agent Usage
- Use sub-agents for: parallel file searches, independent research queries, test execution
- Do NOT use sub-agents for: simple single-file reads, trivial grep, sequential dependent steps
- Each sub-agent gets a focused prompt with only the context it needs
- Merge sub-agent results back with a concise summary

## Observability First
- Every LLM API call must be logged with: timestamp, model, tokens_in, tokens_out, latency_ms
- Every user prompt must be logged with: timestamp, prompt_hash, session_id
- Use structured logging (JSON) — never unstructured print/log statements
- Include trace_id and span_id in all log entries for distributed tracing
