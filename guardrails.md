# Guardrails

Rules and safeguards that enforce deterministic, reproducible code generation.

## Determinism Guardrails

### D-1: Synonym Collapse
All user input is normalized through the canonical verb/noun synonym table **before** any code generation begins.

| Synonyms | Canonical Verb |
|----------|---------------|
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

**Enforcement**: The harness runs synonym normalization as a pre-processing step. If a verb is not in the table, emit an `AMBIGUITY` block — never guess a mapping.

### D-2: Template Binding
Each `CANONICAL_TYPE` maps to exactly one structural template. No style conversion is allowed.

- Arrow functions stay arrow functions
- Named functions stay named functions
- Class methods stay class methods

**Enforcement**: The output validator checks that the implementation structure matches the template for the classified intent type.

### D-3: No Style Opinions
The agent does not make formatting choices. All formatting is delegated to the project's configured formatter.

Defaults (when no formatter config exists):
- Single quotes
- Trailing commas
- 2-space indent
- 80-char line limit

**Enforcement**: Generated code must pass through the formatter unchanged. Any diff = failure.

### D-4: No Comments in Default Output
Comments are not emitted unless:
- The user explicitly requests them
- The intent type is `ASYNC_OPERATION` (error paths must be documented)

**Enforcement**: The output validator strips comments and compares — if semantics are identical, comments were unnecessary.

### D-5: No Imports in Implementation Block
The implementation block contains **only** the function body. Dependencies go in a separate `---DEPENDENCIES---` block.

**Enforcement**: Parser rejects implementation blocks containing `import`/`require`/`from ... import`.

### D-6: Idempotent Regeneration
"Regenerate" or "redo" without prompt changes must produce **byte-for-byte identical** output.

**Enforcement**: The harness stores `content_hash` per intent. On regeneration, hash comparison is mandatory. Mismatch = `DETERMINISM_VIOLATION`.

### D-7: Temperature Lock
All LLM calls use `temperature=0`. If the agent detects variance within a session for the same intent, it must raise `DETERMINISM_VIOLATION` — never silently proceed.

**Enforcement**: The `_check_drift()` method compares content hashes across calls with the same intent key.

## Input Guardrails

### I-1: Intent Classification Required
No code is generated until the intent is classified into a canonical type (`PURE_FUNCTION`, `PREDICATE`, `TRANSFORMER`, `AGGREGATOR`, `SIDE_EFFECT_OP`, `CLASS_METHOD`, `ASYNC_OPERATION`).

### I-2: Ambiguity Halts Generation
If classification confidence is `MEDIUM` or `LOW`, the agent **must** emit an `AMBIGUITY` block and halt. It must never guess or assume.

The ambiguity block contains:
- `unclear_dimension`: what is ambiguous
- `clarifying_question`: a yes/no or choice question
- `assumed_interpretation`: what would be assumed if forced

### I-3: Multi-Function Splitting
Requests for multiple functions are split into N independent sub-intents. Each goes through the full pipeline separately. Functions are never combined into one output block.

### I-4: Spec File Bypass
When a YAML spec file is provided as input, synonym normalization (D-1) is skipped — the spec is already canonical. Proceed directly to template binding (D-2).

## Output Guardrails

### O-1: Schema Validation
Every output must contain all required sections:
- `INTENT_CLASSIFICATION`
- `SIGNATURE`
- `IMPLEMENTATION`
- `INVARIANTS`
- `TEST_ORACLE`

Missing any section = schema violation = automatic retry (up to 3 attempts).

### O-2: Naming Convention Enforcement
- Functions: `<verb><PascalNoun>` — always verbNoun, never nounVerb
- Parameters: fully spelled out nouns, never abbreviations (`firstNumber` not `n1`)
- Collections: plural of the element noun (`users` not `list`)
- Casing matches target language conventions

### O-3: Hash-Based Drift Detection
Every implementation block is hashed (`SHA-256`, first 16 chars). The hash is:
- Stored per intent key (MD5 of the raw intent string)
- Compared on regeneration
- Used for regression testing across sessions

### O-4: Retry Budget
Schema validation failures trigger up to 3 retries with an explicit correction prompt. After 3 failures, raise `ValueError` — never produce unvalidated output.

## Observability Guardrails

### OB-1: Log Every LLM Call
Every call to the Anthropic API must log:
- Request: model, temperature, max_tokens, system prompt hash, user prompt
- Response: content hash, finish_reason, token usage (prompt + completion)
- Metadata: trace_id, span_id, latency_ms, attempt number

### OB-2: Log Every User Prompt
Every user intent must log:
- `prompt_hash`: SHA-256 of the raw prompt
- `session_id`: unique per conversation
- `timestamp_iso`: when received
- `classified_type`: the canonical intent type assigned

### OB-3: Structured Logging Only
All logs use `structlog` with JSON output. No `print()` statements. No unstructured log messages.

### OB-4: Context Window Monitoring
Track cumulative token usage per session. When usage exceeds 40% of the context window:
- Trigger conversation compaction
- Preserve: current task, decisions, file paths, test results
- Discard: intermediate exploration, failed approaches, verbose output
