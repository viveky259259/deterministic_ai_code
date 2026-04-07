# DetermBot — Deterministic Code Generation Agent

A specification-executing agent that produces structurally identical, semantically equivalent code every time the same intent is expressed — regardless of phrasing.

## Design Principles

- **P-1** Determinism over creativity — structural identity across equivalent phrasings, always
- **P-2** Fail loudly, never silently — schema violations and drift events raise exceptions
- **P-3** Separation of concerns — normalisation, classification, generation, validation are independent pipeline stages
- **P-4** Temperature lock is mandatory — `temperature=0` on all API calls, no runtime override
- **P-5** Specs bypass normalisation — YAML/JSON specs skip synonym collapse
- **P-6** One function per output — each pipeline run produces exactly one function

## Build & Test

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the agent
python -m src.main

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_contracts.py -v

# Lint and type check
ruff check src/ tests/
mypy src/

# Determinism regression (hash seed locked)
PYTHONHASHSEED=0 python -m pytest tests/ -v
```

## Architecture

```
src/
  __init__.py
  main.py                        # Entry point
  core/
    __init__.py
    contracts.py                 # All data contracts (enums + dataclasses)
    intent_normalizer.py         # L1 — synonym collapse, verb/noun extraction
    canonical_classifier.py      # L2 — rule-based intent classification
    ambiguity_gate.py            # Gate — halt on confidence < HIGH
    template_binder.py           # L3 — bind classification to structural template
    claude_api_adapter.py        # L4 — Claude API with locked config (temp=0)
    schema_parser.py             # L5 — parse and validate raw output sections
    drift_detector.py            # L5 — session-scoped hash comparison
    retry_orchestrator.py        # Ctrl — retry loop on schema failures (max 3)
    spec_validator.py            # Bypass — YAML/JSON spec input (skips L1+L2)
    agent.py                     # DeterministicCodeAgent — full pipeline orchestrator
    project_spec.py              # Project-level YAML spec parser
    dependency_resolver.py       # Topological sort of generation items
  logging/
    __init__.py
    structured_logger.py         # structlog-based JSON logging
  observability/
    __init__.py
    tracing.py                   # trace_id, span_id, latency tracking
tests/
  __init__.py
  test_contracts.py
  test_intent_normalizer.py
  test_canonical_classifier.py
  test_ambiguity_gate.py
  test_template_binder.py
  test_claude_api_adapter.py
  test_schema_parser.py
  test_drift_detector.py
  test_retry_orchestrator.py
  test_spec_validator.py
  test_agent.py
specs/                           # SDD spec files (YAML)
  INDEX.md                       # Master index + dependency graph + build order
  contracts/                     # 8 data contract specs
  components/                    # 9 pipeline component specs
  features/                      # 21 feature specs (F-01 to F-21)
```

## Pipeline Data Flow

```
raw_input → IntentNormalizer → NormalizedIntent
  → CanonicalClassifier → Classification
  → AmbiguityGate → pass (HIGH) or halt (MEDIUM/LOW → AmbiguityBlock)
  → TemplateBinder → BoundPrompt
  → ClaudeAPIAdapter → RawOutput
  → SchemaParser → ParsedSections (or None → RetryOrchestrator, max 3)
  → DriftDetector → DeterministicResult ✓
```

Spec bypass: `YAML/JSON → SpecValidator → Classification (HIGH) → TemplateBinder → ...`

## Code Patterns

- Python 3.11+, type hints on all public functions
- Structured logging via `structlog` — no `print()` statements
- Every LLM call logged with: model, temperature, tokens, latency_ms, trace_id, span_id
- All configs via environment variables (see `.env.example`)
- `temperature=0` enforced at construction — `AssertionError` on any other value
- Model pinned to `claude-sonnet-4-20250514` — never `"latest"` or `"preview"`

## Key Rules

- Never swallow exceptions — log and re-raise
- All LLM calls go through `ClaudeAPIAdapter` — no direct `anthropic` client usage
- `DETERMINISM_VIOLATION` (RuntimeError) is never caught — always propagates to caller
- Tests required for all new modules before merge
- Keep files under 300 lines; split if larger
- No streaming — `SchemaParser` requires complete output
- System prompt is constant per session — never modified per-request
- Consumers read from `ParsedSections`, never from `raw_output`

## Spec-Driven Development Workflow

1. Read the spec in `specs/` before implementing any module
2. Implement the module following the spec's methods, invariants, and constraints
3. Write tests covering all acceptance criteria from the spec
4. Run `python -m pytest tests/ -v` — all tests must pass before moving on
5. Build order: contracts → components → features (see `specs/INDEX.md`)

## Locked Constants

```python
MODEL       = "claude-sonnet-4-20250514"  # pinned — never "latest"
TEMPERATURE = 0                            # mandatory — determinism lock
MAX_TOKENS  = 2048                         # fixed
```

## Synonym Table (canonical verbs)

| Synonyms | Canonical |
|----------|-----------|
| add, sum, plus, combine | `add` |
| subtract, minus, remove from | `subtract` |
| multiply, times, product | `multiply` |
| divide, split by, quotient | `divide` |
| format, render, display, show | `format` |
| fetch, get, retrieve, pull | `fetch` |
| validate, check, verify, ensure | `validate` |
| transform, convert, map, cast | `transform` |
| calculate, compute, derive | `calculate` |
| save, persist, store, write | `save` |
| define, model, schema, shape, contract | `define` |

## Supported Languages

`javascript` · `typescript` · `python` · `go`

## Canonical Types

`PURE_FUNCTION` · `PREDICATE` · `TRANSFORMER` · `AGGREGATOR` · `SIDE_EFFECT_OP` · `CLASS_METHOD` · `ASYNC_OPERATION` · `DATA_CONTRACT`
