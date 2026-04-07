## SYSTEM: DetermBot — Deterministic Code Generation Agent

DESIGN PRINCIPLES:

  P-1  DETERMINISM OVER CREATIVITY
       The system optimises for structural identity across equivalent phrasings,
       not output quality or stylistic variation. Given identical effective intent,
       all runs must produce byte-for-byte identical implementation blocks.

  P-2  FAIL LOUDLY, NEVER SILENTLY
       Schema violations, drift events, and low-confidence classifications must
       throw exceptions and halt. Silent fallbacks are forbidden — they produce
       non-deterministic output without signalling the violation.

  P-3  SEPARATION OF CONCERNS
       Normalisation, classification, generation, and validation are independent
       pipeline stages. No stage has visibility into another stage's internals.
       Each stage has a typed input contract and a typed output contract.

  P-4  TEMPERATURE LOCK IS MANDATORY
       The Claude API call must always use temperature=0. Any harness that allows
       temperature to be configured at runtime is architecturally incorrect.

  P-5  SPECS BYPASS NORMALISATION
       When the input is a structured YAML/JSON spec, the normalisation and
       classification stages are skipped. The spec is already canonical — feeding
       it through synonym collapse would introduce unnecessary latency and risk.

  P-6  ONE FUNCTION PER OUTPUT
       The system generates exactly one function per pipeline run. Multi-function
       requests are decomposed by the caller into N independent runs.

---

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
    canonical_verb: str          # from synonym table, e.g. "add"
    canonical_noun: str          # PascalCase, e.g. "Total"
    raw_input:      str          # original user string, for tracing
    source:         str          # "freetext" | "yaml_spec" | "json_spec"

@dataclass
class Classification:
    intent_type:    CanonicalType
    confidence:     Confidence
    normalized:     NormalizedIntent
    language:       str          # "javascript" | "python" | "typescript" | "go"

@dataclass
class AmbiguityBlock:
    unclear_dimension:     str
    clarifying_question:   str
    assumed_interpretation: str
    classification:        Classification

@dataclass
class BoundPrompt:
    system_prompt:  str          # full SYSTEM_PROMPT string
    user_message:   str          # "Language: js\nIntent: add two numbers"
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
    sections:       ParsedSections
    content_hash:   str          # SHA-256[:16] of implementation block
    raw_output:     str
    is_ambiguity:   bool = False
    ambiguity:      Optional[AmbiguityBlock] = None

---

## PIPELINE DATA FLOW

HAPPY PATH:
  raw_input
    → IntentNormalizer         → NormalizedIntent
    → CanonicalClassifier      → Classification (confidence=HIGH)
    → AmbiguityGate            → pass-through (no halt)
    → TemplateBinder           → BoundPrompt
    → ClaudeAPIAdapter         → RawOutput
    → SchemaParser             → ParsedSections
    → DriftDetector            → DeterministicResult
    → caller                   ✓

AMBIGUITY PATH (confidence = MEDIUM or LOW):
  Classification (confidence ≠ HIGH)
    → AmbiguityGate            → AmbiguityBlock
    → caller (halt, return block, await user clarification)
  # Pipeline does NOT proceed to TemplateBinder.
  # The caller is responsible for re-entering with a clarified input.

SCHEMA FAILURE PATH (SchemaParser returns None):
  RawOutput
    → SchemaParser             → None
    → RetryOrchestrator        → append schema-violation suffix to BoundPrompt.user_message
    → ClaudeAPIAdapter         → RawOutput (attempt 2)
    → SchemaParser             → ParsedSections (or None → retry again)
  Max retries = 3. If still None after 3 attempts:
    → raise ValueError("Schema validation failed after 3 attempts")

DRIFT VIOLATION PATH:
  DriftDetector detects hash mismatch for same intent_key:
    → raise RuntimeError("DETERMINISM_VIOLATION: ...")
  # Never swallow. Never log-and-continue. Always raise.
  # The operator must investigate before re-running.

SPEC BYPASS PATH (source = "yaml_spec" or "json_spec"):
  parsed_spec
    → SpecValidator            → Classification (confidence always HIGH, no normalisation)
    → TemplateBinder           → BoundPrompt
    → (rest of happy path)

---

## CLAUDE API ADAPTER — CONFIGURATION CONTRACT

LOCKED FIELDS (cannot be overridden at runtime):
  model:       "claude-sonnet-4-20250514"    # pinned version — never "latest"
  temperature: 0                            # CRITICAL — determinism lock
  max_tokens:  2048

VARIABLE FIELDS (set per request):
  system:   SYSTEM_PROMPT (str)             # full prompt from sections 01-06
  messages: [{"role": "user", "content": BoundPrompt.user_message}]

RETRY SUFFIX (appended to user_message on schema failure):
  "\n\nYour previous response did not conform to the required output schema.
  Reformat strictly. Every required section (INTENT_CLASSIFICATION, SIGNATURE,
  IMPLEMENTATION, INVARIANTS, TEST_ORACLE) must be present, delimited by ---,
  with no prose before or after. No alternatives. No explanations."

FORBIDDEN:
  - top_p, top_k, presence_penalty, frequency_penalty (not all exposed, but do not add)
  - streaming (SchemaParser requires complete output before parsing)
  - caching with modified system prompts (breaks determinism if prompt varies between calls)

MODEL PINNING POLICY:
  Model version is pinned at system build time. Upgrades require:
  1. Running the determinism regression suite (see Section 08).
  2. Verifying hash stability across 10 identical runs for all intent types.
  3. Updating the pin in a separate, audited commit.
  Never upgrade models to resolve a single failing test.

---

## SCHEMA PARSER — SECTION GRAMMAR

SECTION DELIMITER:
  Each section is bounded by: ---SECTION_NAME--- ... (next --- or end-of-string)
  Regex: r"---(\w+)---(.*?)(?=---|\Z)"  (re.DOTALL)

REQUIRED SECTIONS:
  INTENT_CLASSIFICATION  — type, confidence, canonical_verb, canonical_noun
  SIGNATURE              — one line per target language
  IMPLEMENTATION         — one fenced code block (```lang ... ```)
  INVARIANTS             — preconditions, postconditions, edge_cases
  TEST_ORACLE            — one fenced code block with ≥3 assertions

OPTIONAL SECTIONS:
  DEPENDENCIES           — present only if non-stdlib imports required
  AMBIGUITY              — present only if confidence ≠ HIGH (pipeline halts here)

IMPLEMENTATION BLOCK EXTRACTION:
  # Strip fences, language tag, and leading/trailing whitespace before hashing.
  raw = sections["IMPLEMENTATION"]
  code = re.sub(r"```\w*\n?", "", raw).strip()
  content_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

PARSE FAILURE CONDITIONS (return None → trigger retry):
  - Any required section is absent
  - IMPLEMENTATION block contains no fenced code
  - AMBIGUITY section is absent but confidence is MEDIUM or LOW
  - More than one fenced code block in IMPLEMENTATION

FORBIDDEN IN IMPLEMENTATION BLOCK:
  - import statements (declare in DEPENDENCIES instead)
  - More than one function definition
  - Prose or comments (unless intent type is ASYNC_OPERATION)

---

## DRIFT DETECTOR — SESSION STATE & VIOLATION PROTOCOL

SESSION MAP:
  A dict[str, str] keyed by intent_key (MD5 of canonical_verb + canonical_noun +
  language + intent_type). Value is content_hash from the first successful run.
  Scoped to a single DeterministicCodeAgent instance (one Python process lifetime).
  Not persisted — each session starts fresh.

HASH STABILITY GUARANTEE:
  For a given intent_key, content_hash must be identical across:
    - Multiple calls within the same session
    - Multiple sessions on the same model version
    - Calls with synonymous phrasings (after normalisation)
  It MAY differ across model version upgrades (trigger regression suite, see §08).

VIOLATION CONDITIONS:
  A DETERMINISM_VIOLATION is raised when:
    same intent_key → different content_hash in the same session.
  It is NOT raised for:
    - New intent_keys (first occurrence always writes to session map)
    - Cross-session differences (cross-session regression is a CI concern, not runtime)

VIOLATION RESPONSE PROTOCOL:
  1. raise RuntimeError with message:
       f"DETERMINISM_VIOLATION\n
          intent_key: {intent_key}\n
          expected:   {session_hashes[intent_key]}\n
          received:   {result.content_hash}\n
          Investigate before re-running."
  2. Do NOT catch this error in the adapter or orchestrator. Let it propagate to caller.
  3. Operator must inspect both raw outputs and identify the divergence source.
  4. Acceptable root causes: system prompt change, model upgrade, synonym table change.
  5. Forbidden responses: silently accepting the new hash, averaging, or ignoring.

---

## DETERMINISM REGRESSION SUITE

PURPOSE:
  Verify that the content_hash is stable across:
    1. Equivalent phrasings (synonym collapse correctness)
    2. Repeated identical calls (idempotency)
    3. Cross-session stability (model + prompt version pinning)

TEST MATRIX:
  For each CanonicalType × each supported language:
    Run 5 calls with the canonical trigger phrase → assert all 5 hashes identical.
    Run 5 calls with 3 synonym phrasings each → assert all 15 hashes identical.
  Total: 7 types × 3 languages × 20 calls = 420 API calls per full regression run.

FAST REGRESSION (pre-merge CI gate, ~60 calls):
  PURE_FUNCTION + PREDICATE in javascript only.
  Must complete in < 90 seconds. Any hash mismatch → block merge.

MANDATORY TRIGGER EVENTS:
  Run full regression before merging any:
  - System prompt edit (any section)
  - Synonym table change (add, edit, remove)
  - Model version upgrade
  - New CanonicalType added
  - New language target added

SAMPLE REGRESSION TEST (pytest):
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

## EXTENSION PROTOCOL

ADDING A NEW CANONICAL TYPE:
  1. Add enum value to CanonicalType.
  2. Add signature template to SYSTEM_PROMPT section 02.
  3. Add ≥2 ground-truth few-shot examples to SYSTEM_PROMPT section 06.
  4. Add trigger-word patterns to IntentNormalizer.
  5. Run full determinism regression suite before merging.

ADDING A NEW SYNONYM:
  1. Add to verb synonym table in SYSTEM_PROMPT Rule D-1.
  2. Add a regression test asserting the synonym produces the same hash
     as the canonical verb for the same intent type and language.
  3. Run fast regression (at minimum).

ADDING A NEW LANGUAGE TARGET:
  1. Add casing rules to SYSTEM_PROMPT section 03.
  2. Add one canonical example per CanonicalType to SYSTEM_PROMPT section 06.
  3. Add language normalizer to IntentNormalizer
     (e.g. "js" → "javascript", "ts" → "typescript").
  4. Run full regression for the new language column only.

ADDING A DOWNSTREAM CONSUMER (formatter, test runner, SDD registry):
  Consumers receive a DeterministicResult and must not re-enter the pipeline.
  If a consumer needs a different format, add a Formatter layer that transforms
  ParsedSections — it must not call the Claude API.

WHAT YOU MUST NEVER DO:
  - Add a "creative mode" flag that raises temperature above 0.
  - Allow system prompt to be configured per-request (breaks session map integrity).
  - Add inline comments to IMPLEMENTATION block (breaks hash stability).
  - Allow consumers to bypass SchemaParser and read RawOutput directly.
  - Combine two functions in a single pipeline run (violates P-6).
