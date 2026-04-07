---
name: observe
description: Add observability instrumentation to a module — tracing, structured logging, and metrics
---

# Observe Skill

When invoked, instrument the target module with:

1. **Structured logging** — Add `structlog` logger to every public function
2. **Tracing spans** — Wrap key operations in OpenTelemetry spans
3. **Metrics** — Add counters/histograms for LLM calls, latency, error rates
4. **Health checks** — Expose a `/health` or `is_healthy()` endpoint if applicable

## Steps
1. Read the target file(s)
2. Identify all public functions and LLM call sites
3. Add `import structlog; logger = structlog.get_logger()` if missing
4. Wrap LLM calls with timing and token logging
5. Add span context propagation
6. Run tests to verify instrumentation doesn't break behavior
