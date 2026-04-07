"""Tracing utilities — trace_id, span_id, latency measurement."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator

from src.logging.structured_logger import get_logger

logger = get_logger("observability.tracing")


def generate_trace_id() -> str:
    """Generate a unique trace ID for a pipeline run."""
    return uuid.uuid4().hex[:16]


def generate_span_id() -> str:
    """Generate a unique span ID for a pipeline stage."""
    return uuid.uuid4().hex[:8]


@dataclass
class SpanContext:
    """Context for a traced span."""

    trace_id: str
    span_id: str
    operation: str
    start_time: float = field(default_factory=time.monotonic)
    latency_ms: float = 0.0


@contextmanager
def traced_span(trace_id: str, operation: str) -> Generator[SpanContext, None, None]:
    """Context manager that tracks latency for a pipeline stage."""
    ctx = SpanContext(
        trace_id=trace_id,
        span_id=generate_span_id(),
        operation=operation,
    )
    try:
        yield ctx
    finally:
        ctx.latency_ms = (time.monotonic() - ctx.start_time) * 1000
        logger.info(
            "span_completed",
            trace_id=ctx.trace_id,
            span_id=ctx.span_id,
            operation=ctx.operation,
            latency_ms=round(ctx.latency_ms, 2),
        )
