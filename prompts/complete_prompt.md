# DetermBot — Deterministic Code Generation Agent

> A canonical code generation harness that produces structurally identical, semantically equivalent code every time the same intent is expressed — regardless of how the user phrases their request.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Design Principles](#2-design-principles)
3. [System Prompt — Agent Identity & Mission](#3-system-prompt--agent-identity--mission)
4. [Canonical Intent Taxonomy](#4-canonical-intent-taxonomy)
5. [Naming Convention Rules](#5-naming-convention-rules)
6. [Output Structure Schema](#6-output-structure-schema)
7. [Determinism Enforcement Rules](#7-determinism-enforcement-rules)
8. [Few-Shot Canonical Examples](#8-few-shot-canonical-examples)
9. [System Architecture](#9-system-architecture)
10. [Component Inventory](#10-component-inventory)
11. [Data Contracts](#11-data-contracts)
12. [Pipeline Data Flow & Error Routing](#12-pipeline-data-flow--error-routing)
13. [Claude API Adapter — Configuration Contract](#13-claude-api-adapter--configuration-contract)
14. [Schema Parser — Section Grammar](#14-schema-parser--section-grammar)
15. [Drift Detector — Session State & Violation Protocol](#15-drift-detector--session-state--violation-protocol)
16. [Determinism Regression Suite](#16-determinism-regression-suite)
17. [Extension Protocol](#17-extension-protocol)
18. [Feature Specs — Full Catalog](#18-feature-specs--full-catalog)
19. [Python Harness Implementation](#19-python-harness-implementation)

---

## 1. System Overview

DetermBot is a **specification-executing agent**, not a creative assistant. Its singular mission is to produce code that is:

- **Structurally identical** across equivalent phrasings
- **Semantically correct** per a formal invariant contract
- **Byte-for-byte reproducible** across sessions on the same model version

Given `"write an add function"`, `"make a sum method"`, or `"create a function to add two numbers"`, DetermBot always returns:

```javascript
const total = (firstNumber, secondNumber) => firstNumber + secondNumber;
```

---

## 2. Design Principles

| # | Principle | Rule |
|---|-----------|------|
| P-1 | Determinism over creativity | Structural identity across phrasings, always |
| P-2 | Fail loudly, never silently | Schema violations and drift events must raise exceptions |
| P-3 | Separation of concerns | Normalisation, classification, generation, validation are independent stages |
| P-4 | Temperature lock is mandatory | `temperature=0` on all API calls, no runtime override |
| P-5 | Specs bypass normalisation | YAML/JSON specs skip synonym collapse and classification |
| P-6 | One function per output | Each pipeline run produces exactly one function |

---

## 3. System Prompt — Agent Identity & Mission

```
## IDENTITY

You are DetermBot, a canonical code generation agent. Your singular mission is to
produce structurally identical, semantically equivalent code every time the same
intent is expressed — regardless of how the user phrases their request.

You do NOT improvise. You do NOT explore alternatives unless explicitly instructed.
You are a specification executor, not a creative assistant.

## CORE CONTRACT

Given any coding intent, you will:
  1. Classify the intent into a canonical intent type (e.g. PURE_FUNCTION, TRANSFORMER,
     PREDICATE, AGGREGATOR, SIDE_EFFECT_OP, CLASS_METHOD, ASYNC_OPERATION)
  2. Apply the canonical signature template for that intent type
  3. Generate code that is byte-for-byte reproducible across all equivalent phrasings

If you are uncertain about the canonical form, output an AMBIGUITY BLOCK and halt.
Never guess. Never paraphrase into a different form. Ask first.
```

---

## 4. Canonical Intent Taxonomy

Classification is the **first step** before generating any code.

### PURE_FUNCTION

- No side effects. Returns a value. No external dependencies.
- Trigger words: `add`, `calculate`, `compute`, `convert`, `format`, `parse`
- Canonical signature: `void <verbNoun>(<typedParams>) => <expression>`
- Example: `void total(firstNumber, secondNumber) => firstNumber + secondNumber`

### PREDICATE

- Returns boolean. Tests a condition. Named with `is`/`has`/`can`/`should`.
- Trigger words: `check`, `validate`, `verify`, `is`, `has`
- Canonical signature: `bool is<Noun>(<typedParams>) => <boolean_expression>`
- Example: `bool isEven(number) => number % 2 === 0`

### TRANSFORMER

- Maps one data structure to another. Pure. Explicit input/output types.
- Trigger words: `transform`, `map`, `normalize`, `serialize`
- Canonical signature: `OutputType to<OutputType>(InputType input) => <mapping>`

### AGGREGATOR

- Reduces a collection to a scalar. Named `reduce`/`sum`/`count`/`collect`.
- Trigger words: `sum`, `count`, `find`, `filter`, `group`, `aggregate`
- Canonical signature: `ResultType reduce<Noun>(Collection<T> items) => <fold>`

### SIDE_EFFECT_OP

- Mutates state, writes to I/O, network calls. Returns void or status.
- Trigger words: `save`, `delete`, `send`, `update`, `write`
- Canonical signature: `async Task<Result> <verb><Noun>(<params>)`

### CLASS_METHOD

- Belongs to a class. Has implicit `self`/`this`.
- Trigger words: `method`, `on`, `for the class`, `inside`, `member`
- Canonical signature: `def <verb>_<noun>(self, <params>) -> ReturnType`

### ASYNC_OPERATION

- I/O-bound, network, or concurrent. Always async/await pattern.
- Trigger words: `fetch`, `await`, `concurrent`, `stream`, `poll`
- Canonical signature: `async def <verb>_<noun>(<params>) -> Awaitable[ReturnType]`

---

## 5. Naming Convention Rules

### Function naming

Pattern: `<verb><PascalNoun>` — always verbNoun, never nounVerb

**Verb normalisation table** — map synonyms to canonical verb:

| Synonyms | Canonical verb |
|----------|---------------|
| `add`, `sum`, `plus`, `combine` | `add` |
| `subtract`, `minus`, `remove from` | `subtract` |
| `multiply`, `times`, `product` | `multiply` |
| `divide`, `split by`, `quotient` | `divide` |
| `format`, `render`, `display`, `show` | `format` |
| `fetch`, `get`, `retrieve`, `pull` | `fetch` |
| `validate`, `check`, `verify`, `ensure` | `validate` |
| `transform`, `convert`, `map`, `cast` | `transform` |
| `calculate`, `compute`, `derive` | `calculate` |
| `save`, `persist`, `store`, `write` | `save` |

### Parameter naming

Parameters are **always** fully spelled out nouns, never abbreviations.

```
✓ firstNumber, secondNumber, userId
✗ a, b, x, y, n1, n2, num1, num2, uid
```

For collection parameters, always use the plural of the element noun:

```
✓ users, orderItems, searchTerms
✗ list, arr, data, items
```

### Casing rules by language

| Language | Functions | Classes | Constants |
|----------|-----------|---------|-----------|
| JavaScript / TypeScript | `camelCase` | `PascalCase` | `SCREAMING_SNAKE` |
| Python | `snake_case` | `PascalCase` | `SCREAMING_SNAKE` |
| Go | `camelCase` (unexported) | `PascalCase` (exported) | — |

---

## 6. Output Structure Schema

Every response must conform to this exact structure. No prose. No alternatives.

```
---INTENT_CLASSIFICATION---
type: <CANONICAL_TYPE>
confidence: <HIGH|MEDIUM|LOW>
canonical_verb: <normalized verb from synonym table>
canonical_noun: <PascalCase noun derived from domain object>

---SIGNATURE---
<language>: <full canonical function signature>

---IMPLEMENTATION---
```<language>
<code block — exactly one function, no surrounding boilerplate>
```

---INVARIANTS---
preconditions:
  - <what must be true about inputs before calling this function>
postconditions:
  - <what is guaranteed to be true about the output>
edge_cases:
  - <enumerate: empty input, null, overflow, type mismatch — and state behavior>

---TEST_ORACLE---
```<language>
<minimum 3 deterministic unit tests using only pure assertions, no mocks>
```
---
```

If confidence is `MEDIUM` or `LOW`, append an AMBIGUITY block instead of code:

```
---AMBIGUITY---
unclear_dimension: <what is ambiguous>
clarifying_question: <single yes/no or choice question to resolve it>
assumed_interpretation: <what you would assume if forced to proceed>
---
```

---

## 7. Determinism Enforcement Rules

### RULE D-1 · Synonym Collapse

Before generating any identifier, run input through the canonical verb/noun synonym table. `"Write me a function that adds two numbers"` and `"Create a method to sum firstNumber and secondNumber"` must produce identical output.

### RULE D-2 · Template Binding

Each `CANONICAL_TYPE` has exactly one structural template. You do not deviate from the template. Arrow functions stay arrow functions. Named functions stay named. Do not convert between styles based on perceived preference.

### RULE D-3 · No Style Opinions

You do not choose between single-quote and double-quote. You do not choose between trailing commas and no trailing commas. The harness sets a `.editorconfig` and a `prettier.config`.

> Default: single quotes, trailing commas, 2-space indent, 80-char line limit.

### RULE D-4 · No Comments in Default Output

Do not emit inline comments unless the user explicitly requests them or the intent type is `ASYNC_OPERATION`. The oracle block is the documentation.

### RULE D-5 · No Imports in Implementation Block

The implementation block contains only the function. Dependencies are declared in a separate `---DEPENDENCIES---` block if and only if a non-stdlib import is required.

### RULE D-6 · Idempotent Regeneration

If the user says "regenerate" or "redo" without changing the prompt, your output **must** be byte-for-byte identical to the previous output. If you cannot guarantee this, emit an `AMBIGUITY` block explaining what introduces variance.

### RULE D-7 · Temperature Lock

You are operating at `temperature=0`. If you detect you are producing two different implementations for the same intent within a session, flag this as a `DETERMINISM_VIOLATION` error — do not silently proceed.

---

## 8. Few-Shot Canonical Examples

### Example 1 — Add function (PURE_FUNCTION)

Any of: `"write add function"`, `"make a sum method"`, `"create a function to add two numbers"`, `"I need addition"`

```
---INTENT_CLASSIFICATION---
type: PURE_FUNCTION
confidence: HIGH
canonical_verb: add
canonical_noun: Total

---SIGNATURE---
javascript: void total(firstNumber, secondNumber) => firstNumber + secondNumber

---IMPLEMENTATION---
```javascript
const total = (firstNumber, secondNumber) => firstNumber + secondNumber;
```

---INVARIANTS---
preconditions:
  - firstNumber must be a finite number (not NaN, not Infinity)
  - secondNumber must be a finite number (not NaN, not Infinity)
postconditions:
  - returns a number equal to the arithmetic sum of both inputs
  - return type is always number
edge_cases:
  - (0, 0) => 0
  - (-5, 5) => 0
  - (Number.MAX_SAFE_INTEGER, 1) => precision loss — caller responsibility

---TEST_ORACLE---
```javascript
assert(total(1, 2) === 3);
assert(total(0, 0) === 0);
assert(total(-1, 1) === 0);
assert(Math.abs(total(0.1, 0.2) - 0.3) < Number.EPSILON);
```
---
```

### Example 2 — Even number check (PREDICATE)

Any of: `"check if even"`, `"is it an even number"`, `"write even validator"`, `"function to detect even"`

```
---INTENT_CLASSIFICATION---
type: PREDICATE
confidence: HIGH
canonical_verb: validate
canonical_noun: EvenNumber

---IMPLEMENTATION---
```javascript
const isEvenNumber = (number) => number % 2 === 0;
```

---TEST_ORACLE---
```javascript
assert(isEvenNumber(2) === true);
assert(isEvenNumber(3) === false);
assert(isEvenNumber(0) === true);
assert(isEvenNumber(-4) === true);
```
---
```

---

## 9. System Architecture

```
User intent ("write add function" / YAML spec)
         │
         ▼
┌─────────────────────────────────┐
│  Layer 1 · Intent normalizer    │
│  Synonym collapse │ Verb lookup │ Spec-bypass gate
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Layer 2 · Canonical classifier │
│  PURE_FUNCTION · PREDICATE · TRANSFORMER · AGGREGATOR · SIDE_EFFECT_OP · ASYNC_OP
└─────────────────────────────────┘
         │
         ▼
    ◇ Confidence?
   HIGH ──────────────────────────────────────────────────────────►
   LOW/MEDIUM ──────────► AMBIGUITY BLOCK (halt, ask user)

         │ (HIGH path)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  System prompt harness                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 3 · Template binder                              │   │
│  │  Canonical signature → type template → naming rules     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 4 · Claude API call                              │   │
│  │  temperature=0 · model=claude-sonnet-4 · max_tokens=2048│   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 5 · Structured output                            │   │
│  │  INTENT_CLASSIFICATION · SIGNATURE · IMPLEMENTATION     │   │
│  │  INVARIANTS · TEST_ORACLE · DEPENDENCIES (optional)     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python validation harness                                      │
│  ┌──────────────────┐     ┌──────────────────────────────┐     │
│  │  Schema parser   │────►│  Drift detector              │     │
│  │  Regex section   │     │  SHA-256 · session map       │     │
│  └──────────────────┘     └──────────────────────────────┘     │
│  ◄─── retry (max 3) ───────────────────────────────────────    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
Validated DeterministicResult
(raw · content_hash · sections · is_ambiguity)
         │
         ▼
Downstream consumer (formatter · test runner · SDD registry)
```

---

## 10. Component Inventory

| Component | Layer | Responsibility | Input | Output |
|-----------|-------|----------------|-------|--------|
| `IntentNormalizer` | L1 | Collapse synonyms → canonical verb+noun | Raw user string | `NormalizedIntent` |
| `CanonicalClassifier` | L2 | Map NormalizedIntent → CanonicalType + confidence | `NormalizedIntent` | `Classification` |
| `AmbiguityGate` | gate | Halt pipeline when confidence < HIGH | `Classification` | `AmbiguityBlock` or pass-through |
| `TemplateBinder` | L3 | Bind Classification → structural prompt template | `Classification` | `BoundPrompt` |
| `ClaudeAPIAdapter` | L4 | Call Claude at temp=0 with BoundPrompt + SYSTEM_PROMPT | `BoundPrompt` | `RawOutput` |
| `SchemaParser` | L5 | Parse RawOutput → typed section dict | `RawOutput` | `ParsedSections` or `None` |
| `DriftDetector` | L5 | Hash IMPLEMENTATION block, compare to session map | `ParsedSections` + session map | `DeterministicResult` or VIOLATION |
| `RetryOrchestrator` | ctrl | Re-enter pipeline at L4 on schema failure (max 3) | `None` from SchemaParser | `DeterministicResult` or `ValueError` |

---

## 11. Data Contracts

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class CanonicalType(Enum):
    PURE_FUNCTION    = "PURE_FUNCTION"
    PREDICATE        = "PREDICATE"
    TRANSFORMER      = "TRANSFORMER"
    AGGREGATOR       = "AGGREGATOR"
    SIDE_EFFECT_OP   = "SIDE_EFFECT_OP"
    CLASS_METHOD     = "CLASS_METHOD"
    ASYNC_OPERATION  = "ASYNC_OPERATION"

class Confidence(Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"

@dataclass
class NormalizedIntent:
    canonical_verb: str       # from synonym table, e.g. "add"
    canonical_noun: str       # PascalCase, e.g. "Total"
    raw_input:      str       # original user string, for tracing
    source:         str       # "freetext" | "yaml_spec" | "json_spec"

@dataclass
class Classification:
    intent_type:  CanonicalType
    confidence:   Confidence
    normalized:   NormalizedIntent
    language:     str         # "javascript" | "python" | "typescript" | "go"

@dataclass
class AmbiguityBlock:
    unclear_dimension:      str
    clarifying_question:    str
    assumed_interpretation: str
    classification:         Classification

@dataclass
class BoundPrompt:
    system_prompt:  str       # full SYSTEM_PROMPT string
    user_message:   str       # "Language: js\nIntent: add two numbers"
    classification: Classification

@dataclass
class ParsedSections:
    intent_classification: str
    signature:             str
    implementation:        str
    invariants:            str
    test_oracle:           str
    dependencies:          Optional[str] = None

@dataclass
class DeterministicResult:
    sections:     ParsedSections
    content_hash: str         # SHA-256[:16] of implementation block
    raw_output:   str
    is_ambiguity: bool = False
    ambiguity:    Optional[AmbiguityBlock] = None
```

---

## 12. Pipeline Data Flow & Error Routing

### Happy path

```
raw_input
  → IntentNormalizer         → NormalizedIntent
  → CanonicalClassifier      → Classification (confidence=HIGH)
  → AmbiguityGate            → pass-through
  → TemplateBinder           → BoundPrompt
  → ClaudeAPIAdapter         → RawOutput
  → SchemaParser             → ParsedSections
  → DriftDetector            → DeterministicResult  ✓
```

### Ambiguity path (confidence = MEDIUM or LOW)

```
Classification (confidence ≠ HIGH)
  → AmbiguityGate            → AmbiguityBlock
  → caller (halt, return block, await user clarification)
```

Pipeline does **not** proceed to TemplateBinder. The caller is responsible for re-entering with a clarified input.

### Schema failure path

```
RawOutput → SchemaParser → None
  → RetryOrchestrator → append schema-violation suffix to BoundPrompt.user_message
  → ClaudeAPIAdapter  → RawOutput (attempt 2)
  → ...
```

Max retries = 3. If still `None` after 3 attempts → `raise ValueError("Schema validation failed after 3 attempts")`.

### Drift violation path

```
DriftDetector detects hash mismatch for same intent_key:
  → raise RuntimeError("DETERMINISM_VIOLATION: ...")
```

Never swallow. Never log-and-continue. Always raise.

### Spec bypass path

```
parsed_spec
  → SpecValidator           → Classification (confidence always HIGH, no normalisation)
  → TemplateBinder          → BoundPrompt
  → (rest of happy path)
```

---

## 13. Claude API Adapter — Configuration Contract

### Locked fields (cannot be overridden at runtime)

```python
model:       "claude-sonnet-4-20250514"   # pinned version — never "latest"
temperature: 0                            # CRITICAL — determinism lock
max_tokens:  2048
```

### Variable fields (set per request)

```python
system:   SYSTEM_PROMPT                   # full prompt from sections 3-8
messages: [{"role": "user", "content": BoundPrompt.user_message}]
```

### Retry suffix (appended to user_message on schema failure)

```
"\n\nYour previous response did not conform to the required output schema.
Reformat strictly. Every required section (INTENT_CLASSIFICATION, SIGNATURE,
IMPLEMENTATION, INVARIANTS, TEST_ORACLE) must be present, delimited by ---,
with no prose before or after. No alternatives. No explanations."
```

### Forbidden

- `top_p`, `top_k`, `presence_penalty`, `frequency_penalty`
- Streaming (SchemaParser requires complete output before parsing)
- Caching with modified system prompts

### Model pinning policy

Model version is pinned at system build time. Upgrades require:
1. Running the determinism regression suite (see §16)
2. Verifying hash stability across 10 identical runs for all intent types
3. Updating the pin in a separate, audited commit

---

## 14. Schema Parser — Section Grammar

### Section delimiter

```
---SECTION_NAME---
```

Regex: `r"---(\w+)---(.*?)(?=---|\Z)"` with `re.DOTALL`

### Required sections

| Section | Contents |
|---------|----------|
| `INTENT_CLASSIFICATION` | type, confidence, canonical_verb, canonical_noun |
| `SIGNATURE` | one line per target language |
| `IMPLEMENTATION` | one fenced code block |
| `INVARIANTS` | preconditions, postconditions, edge_cases |
| `TEST_ORACLE` | one fenced code block with ≥3 assertions |

### Optional sections

| Section | When present |
|---------|-------------|
| `DEPENDENCIES` | Only if non-stdlib import required |
| `AMBIGUITY` | Only if confidence ≠ HIGH (pipeline halts) |

### Implementation block extraction

```python
raw = sections["IMPLEMENTATION"]
code = re.sub(r"```\w*\n?", "", raw).strip()
content_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
```

### Parse failure conditions (return `None` → trigger retry)

- Any required section is absent
- `IMPLEMENTATION` block contains no fenced code
- `AMBIGUITY` section absent but confidence is `MEDIUM` or `LOW`
- More than one fenced code block in `IMPLEMENTATION`

---

## 15. Drift Detector — Session State & Violation Protocol

### Session map

```python
dict[str, str]
# key:   MD5(canonical_verb + canonical_noun + language + intent_type)
# value: SHA-256[:16] of implementation block
```

Scoped to a single `DeterministicCodeAgent` instance. Not persisted between sessions.

### Hash stability guarantee

For a given `intent_key`, `content_hash` must be identical across:
- Multiple calls within the same session
- Multiple sessions on the same model version
- Calls with synonymous phrasings (after normalisation)

### Violation conditions

A `DETERMINISM_VIOLATION` is raised when: **same `intent_key` → different `content_hash`** in the same session.

### Violation response protocol

```python
raise RuntimeError(
    f"DETERMINISM_VIOLATION\n"
    f"  intent_key: {intent_key}\n"
    f"  expected:   {session_hashes[intent_key]}\n"
    f"  received:   {result.content_hash}\n"
    f"  Investigate before re-running."
)
```

Do **not** catch this error in the adapter or orchestrator. Let it propagate to caller.

---

## 16. Determinism Regression Suite

### Full regression (420 calls)

For each `CanonicalType` (7) × language (3: js, ts, py):
- 5 calls with canonical trigger phrase → assert all hashes identical
- 5 calls with each of 3 synonym phrasings → assert all 15 hashes identical

Total: 7 × 3 × 20 = **420 API calls**

### Fast regression (60 calls — CI pre-merge gate)

`PURE_FUNCTION` + `PREDICATE` × JavaScript only. Must complete in < 90 seconds.

### Mandatory trigger events

Run full regression before merging any:
- System prompt edit (any section)
- Synonym table change (add, edit, remove)
- Model version upgrade
- New `CanonicalType` added
- New language target added

### Sample regression test

```python
@pytest.mark.parametrize("phrase", [
    "write add function",
    "create a method to sum two numbers",
    "I need a function that adds firstNumber and secondNumber",
    "make an addition function",
])
def test_add_hash_stability(phrase, agent):
    results = [agent.generate(phrase, "javascript") for _ in range(5)]
    hashes  = [r.content_hash for r in results]
    assert len(set(hashes)) == 1, f"Drift detected: {set(hashes)}"
```

---

## 17. Extension Protocol

### Adding a new canonical type

1. Add enum value to `CanonicalType`
2. Add signature template to SYSTEM_PROMPT §4
3. Add ≥2 ground-truth few-shot examples to SYSTEM_PROMPT §8
4. Add trigger-word patterns to `IntentNormalizer`
5. Run full determinism regression suite before merging

### Adding a new synonym

1. Add to verb synonym table in Rule D-1
2. Add a regression test asserting the synonym produces the same hash as the existing canonical trigger word

### Adding a new language target

1. Add casing rules to SYSTEM_PROMPT §5
2. Add one canonical example per `CanonicalType` to SYSTEM_PROMPT §8
3. Add language normalizer alias to `IntentNormalizer`
4. Run full regression for the new language column only

### What you must never do

- Add a "creative mode" flag that raises temperature above `0`
- Allow system prompt to be configured per-request
- Add inline comments to `IMPLEMENTATION` block
- Allow consumers to bypass `SchemaParser` and read `RawOutput` directly
- Combine two functions in a single pipeline run

---

## 18. Feature Specs — Full Catalog

### F-01 · Free-text intent input `[INPUT · P0]`

**Description:** Accepts a raw natural language string and routes it into the normalisation pipeline.

| Field | Value |
|-------|-------|
| Input | `user_intent: str`, `language: str` |
| Output | `NormalizedIntent` |
| Source tag | `"freetext"` |

**Processing rules:**
- Strip leading/trailing whitespace and normalise unicode (NFKC)
- Lowercase before synonym table lookup
- If input is empty or < 3 chars → `raise ValueError("Intent too short")`
- If input contains YAML front matter → route to F-02

**Acceptance criteria:**
- ✓ `"write add function"` → `canonical_verb="add"`, `canonical_noun="Total"`
- ✓ `"CREATE A METHOD TO SUM TWO NUMBERS"` → identical to above (case-insensitive)
- ✓ `""` → raises `ValueError`

---

### F-02 · YAML / JSON spec input `[INPUT · P0]`

**Description:** Accepts a structured spec file as canonical input, bypassing synonym collapse and classification.

```yaml
intent: pure_function
verb: add
noun: Total
params:
  - name: firstNumber
    type: number
  - name: secondNumber
    type: number
returns: number
language: javascript
```

**Pipeline shortcut:** `SpecValidator → Classification (confidence always HIGH)`

**Acceptance criteria:**
- ✓ Valid YAML spec → `Classification` with `confidence=HIGH`, no synonym lookup
- ✓ Missing `"verb"` field → raises `SchemaError("Missing required field: verb")`

---

### F-03 · Multi-language targeting `[INPUT · P0]`

**Language normaliser table:**

| Aliases | Canonical |
|---------|-----------|
| `"js"`, `"javascript"` | `"javascript"` |
| `"ts"`, `"typescript"` | `"typescript"` |
| `"py"`, `"python"`, `"python3"` | `"python"` |
| `"go"`, `"golang"` | `"go"` |

**Acceptance criteria:**
- ✓ `language="js"` → normalises to `"javascript"`
- ✓ `language="rust"` → raises `ValueError`
- ✓ Python output uses `snake_case`

---

### F-04 · Multi-function decomposition `[INPUT · P1]`

**Description:** Splits multiple intents into N independent pipeline runs.

**Acceptance criteria:**
- ✓ `"write add and subtract functions"` → 2 independent pipeline runs
- ✓ Result list length == number of detected sub-intents
- ✓ Sub-intent failure does not block subsequent sub-intents
- ! `"make a calculator"` → treated as SINGLE intent, not decomposed

---

### F-05 · Synonym collapse `[NORMALISATION · P0]`

**Description:** Maps every synonym to a canonical verb, the primary determinism mechanism.

**Acceptance criteria:**
- ✓ `"sum"` → `canonical_verb = "add"`
- ✓ `"retrieve user"` → `canonical_verb = "fetch"`
- ✓ `"frobnicate"` → no match → `confidence = LOW` → `AmbiguityBlock`
- ✓ Same `canonical_verb` + same language → same `content_hash`

---

### F-06 · Canonical intent classifier `[NORMALISATION · P0]`

**Classification rules:**

| Type | Conditions |
|------|-----------|
| `PURE_FUNCTION` | canonical_verb in {add, subtract, multiply, divide, calculate, format, transform} AND no I/O keywords |
| `PREDICATE` | intent contains is/has/can/should OR canonical_verb = validate |
| `TRANSFORMER` | "to", "from", "into" present OR canonical_verb = transform |
| `AGGREGATOR` | collection nouns + reduce/sum/count/group |
| `SIDE_EFFECT_OP` | canonical_verb in {save, delete, send, update, write} |
| `CLASS_METHOD` | "method", "on class", "inside", "member of" present |
| `ASYNC_OPERATION` | canonical_verb = fetch OR "async"/"await"/"concurrent" present |

**Confidence rules:**
- `HIGH` — exactly one type matches
- `MEDIUM` — two types could match
- `LOW` — no type matches or verb is unrecognised

---

### F-07 · Ambiguity gate `[NORMALISATION · P0]`

**Description:** Hard gate between `CanonicalClassifier` and `TemplateBinder`. Halts on any confidence < HIGH.

**Acceptance criteria:**
- ✓ `MEDIUM` confidence → returns `AmbiguityBlock`, does NOT call Claude API
- ✓ `LOW` confidence → returns `AmbiguityBlock` with `clarifying_question`
- ✓ `AmbiguityBlock` is NOT an exception — it is a valid return value

---

### F-08 · Naming convention enforcer `[NORMALISATION · P0]`

**Function name rules by type:**

| Type | Name pattern |
|------|-------------|
| `PURE_FUNCTION` | noun only (`total`, not `addTotal`) |
| `PREDICATE` | prefix `is` (`isEvenNumber`) |
| `TRANSFORMER` | prefix `to` (`toUserDto`) |
| `AGGREGATOR` | prefix `reduce` or noun (`sumOrders`) |

**Acceptance criteria:**
- ✓ `PURE_FUNCTION + "add" + "Total"` → function name: `total`
- ✓ `PREDICATE + "validate" + "EvenNumber"` → function name: `isEvenNumber`
- ✓ 2 numeric params → always `firstNumber`, `secondNumber`

---

### F-09 · Template binder `[GENERATION · P0]`

**Template per type:**

```
PURE_FUNCTION  : const {name} = ({params}) => {expression};
PREDICATE      : const {name} = ({param}) => {boolean_expression};
TRANSFORMER    : const {name} = ({param}: {InputType}): {OutputType} => ({mapping});
AGGREGATOR     : const {name} = ({params}: {T}[]): {ResultType} => {fold};
SIDE_EFFECT_OP : async function {name}({params}): Promise<{Result}> { ... }
CLASS_METHOD   : {name}({params}): {ReturnType} { ... }
ASYNC_OPERATION: async function {name}({params}): Promise<{ReturnType}> { ... }
```

**Acceptance criteria:**
- ✓ `PURE_FUNCTION` → always produces arrow function, never named function
- ✓ `SIDE_EFFECT_OP` → always async, always returns `Promise`
- ✓ Equivalent phrasings → identical `BoundPrompt.user_message`

---

### F-10 · Structured output schema `[GENERATION · P0]`

See [§6 — Output Structure Schema](#6-output-structure-schema) for full schema definition.

**Acceptance criteria:**
- ✓ All 5 required sections present → `SchemaParser` returns `ParsedSections`
- ✓ Any section missing → `SchemaParser` returns `None` → `RetryOrchestrator` fires
- ✓ `IMPLEMENTATION` contains exactly one fenced code block

---

### F-11 · Invariant generation `[GENERATION · P0]`

**Invariant structure:**
- `preconditions` — what must be true about inputs before calling
- `postconditions` — what is guaranteed to be true about the output
- `edge_cases` — enumerated behaviours for boundary/degenerate inputs

**Acceptance criteria:**
- ✓ All three sub-sections present
- ✓ Each precondition references a named parameter
- ✓ At least one numeric edge case stated
- ✓ No `"see implementation"` in edge_cases

---

### F-12 · Test oracle generation `[GENERATION · P0]`

**Oracle rules:**
- Minimum 3 assertions per function
- Pure assertions only: `assert(expr === expected)` or equivalent
- No mocks, stubs, spies, or describe/it blocks
- Floating-point comparisons must use epsilon

**Acceptance criteria:**
- ✓ ≥ 3 assertions present
- ✓ No describe/it/test wrappers
- ✓ All inputs are literals

---

### F-13 · Schema parser `[VALIDATION · P0]`

See [§14 — Schema Parser](#14-schema-parser--section-grammar).

---

### F-14 · Drift detector `[VALIDATION · P0]`

See [§15 — Drift Detector](#15-drift-detector--session-state--violation-protocol).

---

### F-15 · Retry harness `[VALIDATION · P0]`

**Acceptance criteria:**
- ✓ Schema failure on attempt 1 → retries with suffix
- ✓ Schema failure on all 3 attempts → raises `ValueError`
- ✓ Retry does NOT re-run normalisation or classification
- ✓ `temperature=0` on all retry API calls

---

### F-16 · Temperature lock `[DETERMINISM · P0]`

```python
MODEL       = "claude-sonnet-4-20250514"  # pinned
TEMPERATURE = 0                           # constant, not configurable
```

**Acceptance criteria:**
- ✓ All API calls use `temperature=0`
- ✓ `MODEL` string does not contain `"latest"` or `"preview"`
- ✓ Attempting to construct adapter with `temperature != 0` → `AssertionError`

---

### F-17 · Idempotent regeneration `[DETERMINISM · P0]`

**Mechanism:** idempotency is emergent from the pipeline — same input → same `NormalizedIntent` → same `Classification` → same `BoundPrompt` → same `RawOutput` → same `content_hash`.

**Acceptance criteria:**
- ✓ `agent.generate("write add function")` × 10 → 10 identical `content_hash` values
- ✓ `"sum"` and `"add"` → same hash (synonym collapse makes them identical)

---

### F-18 · Determinism regression suite `[DETERMINISM · P0]`

See [§16 — Determinism Regression Suite](#16-determinism-regression-suite).

---

### F-19 · New intent type protocol `[EXTENSION · P1]`

5-step protocol: enum → classification rules → template → few-shot examples → regression.

---

### F-20 · New language target `[EXTENSION · P1]`

4-step protocol: alias → casing rules → canonical examples → regression (new language column only).

---

### F-21 · Downstream consumer API `[EXTENSION · P1]`

**Consumer contract:**
- Consumers receive a `DeterministicResult` (typed)
- Consumers read from `sections` (`ParsedSections`), not from `raw_output`
- Consumers never modify implementation code (read-only)
- Consumers must not call `ClaudeAPIAdapter` independently

**Built-in consumer types:**

| Consumer | Description |
|----------|-------------|
| `Formatter` | `ParsedSections` → formatted string |
| `TestRunner` | `test_oracle` → execute assertions, return pass/fail |
| `SDDRegistry` | `DeterministicResult` → persist to spec store (`content_hash` as key) |
| `DependencyGraph` | `dependencies` → build import graph |

---

## 19. Python Harness Implementation

```python
import anthropic
import re
import hashlib
from dataclasses import dataclass
from typing import Optional

SYSTEM_PROMPT = """<paste full prompt from sections 3-8 here>"""

MODEL       = "claude-sonnet-4-20250514"
TEMPERATURE = 0
MAX_TOKENS  = 2048

REQUIRED_SECTIONS = [
    "INTENT_CLASSIFICATION",
    "SIGNATURE",
    "IMPLEMENTATION",
    "INVARIANTS",
    "TEST_ORACLE",
]

@dataclass
class ParsedSections:
    intent_classification: str
    signature:             str
    implementation:        str
    invariants:            str
    test_oracle:           str
    dependencies:          Optional[str] = None

@dataclass
class DeterministicResult:
    raw_output:   str
    content_hash: str
    sections:     Optional[ParsedSections]
    is_ambiguity: bool = False


class DeterministicCodeAgent:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.session_hashes: dict[str, str] = {}

    def generate(
        self,
        user_intent: str,
        language: str = "javascript",
        max_retries: int = 3,
    ) -> DeterministicResult:
        """Generate deterministic code with schema validation and drift detection."""
        language  = self._normalise_language(language)
        prompt    = f"Language target: {language}\nIntent: {user_intent}"

        for attempt in range(max_retries):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw    = response.content[0].text
            result = self._parse_and_validate(raw)

            if result is not None:
                self._check_drift(user_intent, language, result)
                return result

            if attempt < max_retries - 1:
                prompt += (
                    "\n\nYour previous response did not conform to the required output schema. "
                    "Reformat strictly — no prose, no alternatives."
                )

        raise ValueError(f"Schema validation failed after {max_retries} attempts")

    # ── private helpers ──────────────────────────────────────────────────────

    def _normalise_language(self, lang: str) -> str:
        table = {
            "js": "javascript", "javascript": "javascript",
            "ts": "typescript", "typescript": "typescript",
            "py": "python",     "python": "python", "python3": "python",
            "go": "go",         "golang": "go",
        }
        key = lang.lower().strip()
        if key not in table:
            raise ValueError(f"Unsupported language: {lang}")
        return table[key]

    def _parse_and_validate(self, raw: str) -> Optional[DeterministicResult]:
        if "---AMBIGUITY---" in raw:
            return DeterministicResult(raw, "", None, is_ambiguity=True)

        sections: dict[str, str] = {}
        for name in REQUIRED_SECTIONS:
            pattern = rf"---{name}---(.*?)(?=---|$)"
            match   = re.search(pattern, raw, re.DOTALL)
            if not match:
                return None  # schema violation → trigger retry
            sections[name] = match.group(1).strip()

        # Extract implementation code (strip fences)
        code = re.sub(r"```\w*\n?", "", sections["IMPLEMENTATION"]).strip()
        content_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

        parsed = ParsedSections(
            intent_classification = sections["INTENT_CLASSIFICATION"],
            signature             = sections["SIGNATURE"],
            implementation        = code,
            invariants            = sections["INVARIANTS"],
            test_oracle           = sections["TEST_ORACLE"],
            dependencies          = sections.get("DEPENDENCIES"),
        )
        return DeterministicResult(raw, content_hash, parsed)

    def _check_drift(
        self,
        user_intent: str,
        language: str,
        result: DeterministicResult,
    ) -> None:
        intent_key = hashlib.md5(
            f"{user_intent}:{language}".encode()
        ).hexdigest()

        if intent_key in self.session_hashes:
            previous = self.session_hashes[intent_key]
            if previous != result.content_hash:
                raise RuntimeError(
                    f"DETERMINISM_VIOLATION\n"
                    f"  intent_key: {intent_key}\n"
                    f"  expected:   {previous}\n"
                    f"  received:   {result.content_hash}"
                )
        self.session_hashes[intent_key] = result.content_hash


# ── usage ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent  = DeterministicCodeAgent(api_key="YOUR_API_KEY")
    result = agent.generate("write add function", language="javascript")

    print(result.sections.implementation)
    print(f"Hash: {result.content_hash}")
```

---

## Quick Reference

### Supported languages

`javascript` · `typescript` · `python` · `go`

### Canonical types

`PURE_FUNCTION` · `PREDICATE` · `TRANSFORMER` · `AGGREGATOR` · `SIDE_EFFECT_OP` · `CLASS_METHOD` · `ASYNC_OPERATION`

### Output sections

`INTENT_CLASSIFICATION` · `SIGNATURE` · `IMPLEMENTATION` · `INVARIANTS` · `TEST_ORACLE` · `DEPENDENCIES` (optional)

### Confidence levels

- `HIGH` → pipeline continues to generation
- `MEDIUM` / `LOW` → `AmbiguityBlock` returned, pipeline halts

### Key invariants

- `temperature = 0` always
- Model version pinned (never `"latest"`)
- One function per pipeline run
- Schema failure → retry up to 3 times
- Hash mismatch → `DETERMINISM_VIOLATION` raised (never swallowed)

---

*DetermBot — spec version 1.0.0*
