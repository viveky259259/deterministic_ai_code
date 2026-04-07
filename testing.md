# Testing Process

Comprehensive testing strategy for the deterministic code generation agent.

## Test Categories

### 1. Determinism Tests
Verify that the same intent always produces the same output.

```python
# test_determinism.py

def test_identical_output_across_runs():
    """Same intent must produce byte-for-byte identical code."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    results = [agent.generate("write add function") for _ in range(5)]
    hashes = [r.content_hash for r in results]
    assert len(set(hashes)) == 1, f"Drift detected: {hashes}"


def test_synonym_produces_same_hash():
    """All synonym phrasings must resolve to the same canonical output."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    phrasings = [
        "write add function",
        "make a sum method",
        "create a function to add two numbers",
        "I need addition",
    ]
    hashes = [agent.generate(p).content_hash for p in phrasings]
    assert len(set(hashes)) == 1, f"Synonym collapse failed: {hashes}"


def test_regenerate_is_idempotent():
    """Saying 'regenerate' without changing prompt = identical output."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    first = agent.generate("check if even")
    second = agent.generate("check if even")
    assert first.content_hash == second.content_hash


def test_determinism_violation_raises():
    """If drift is detected within a session, RuntimeError must be raised."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    agent.session_hashes["test_key"] = "previous_hash"
    # Manually trigger drift detection
    result = DeterministicResult(
        raw_output="", content_hash="different_hash", sections={}, is_ambiguity=False
    )
    with pytest.raises(RuntimeError, match="DETERMINISM_VIOLATION"):
        agent._check_drift("test_key", result)
```

### 2. Schema Validation Tests
Verify that outputs conform to the required structure.

```python
# test_schema.py

REQUIRED_SECTIONS = [
    "INTENT_CLASSIFICATION", "SIGNATURE",
    "IMPLEMENTATION", "INVARIANTS", "TEST_ORACLE",
]


def test_all_sections_present():
    """Every non-ambiguity output must contain all required sections."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("write add function")
    assert not result.is_ambiguity
    for section in REQUIRED_SECTIONS:
        assert section in result.sections, f"Missing section: {section}"


def test_ambiguity_block_on_unclear_intent():
    """Unclear intents must produce AMBIGUITY block, not code."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("do something with the data")
    assert result.is_ambiguity


def test_implementation_has_no_imports():
    """Implementation block must not contain import statements."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("fetch user by id")
    impl = result.sections["IMPLEMENTATION"]
    assert "import " not in impl
    assert "require(" not in impl
    assert "from " not in impl or "from " not in impl.split("```")[0]


def test_retry_on_schema_failure():
    """Schema violations trigger retries up to max_retries."""
    # Mock the API to return malformed output twice, then valid output
    # Assert that the agent retries and eventually succeeds
    pass


def test_max_retries_raises_value_error():
    """Exceeding max_retries raises ValueError."""
    # Mock the API to always return malformed output
    # Assert ValueError after max_retries
    pass
```

### 3. Intent Classification Tests
Verify correct mapping from user input to canonical types.

```python
# test_classification.py

CLASSIFICATION_CASES = [
    # (input, expected_type, expected_verb)
    ("write add function", "PURE_FUNCTION", "add"),
    ("make a sum method", "PURE_FUNCTION", "add"),
    ("check if even", "PREDICATE", "validate"),
    ("is it a valid email", "PREDICATE", "validate"),
    ("transform user to DTO", "TRANSFORMER", "transform"),
    ("convert response to JSON", "TRANSFORMER", "transform"),
    ("count active users", "AGGREGATOR", "count"),
    ("sum all order totals", "AGGREGATOR", "add"),
    ("save user to database", "SIDE_EFFECT_OP", "save"),
    ("delete the record", "SIDE_EFFECT_OP", "delete"),
    ("fetch user profile", "ASYNC_OPERATION", "fetch"),
    ("stream events from queue", "ASYNC_OPERATION", "stream"),
]


@pytest.mark.parametrize("intent,expected_type,expected_verb", CLASSIFICATION_CASES)
def test_intent_classification(intent, expected_type, expected_verb):
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate(intent)
    classification = result.sections["INTENT_CLASSIFICATION"]
    assert f"type: {expected_type}" in classification
    assert f"canonical_verb: {expected_verb}" in classification
```

### 4. Naming Convention Tests
Verify that generated identifiers follow canonical rules.

```python
# test_naming.py

def test_function_name_is_verb_noun():
    """Function names must be <verb><PascalNoun>."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("write add function", language="javascript")
    impl = result.sections["IMPLEMENTATION"]
    # Must contain 'total' or 'addTotal', not 'numbersAdd'
    assert "total" in impl.lower()


def test_parameters_are_descriptive():
    """Parameters must be fully spelled out, not abbreviated."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("write add function", language="javascript")
    impl = result.sections["IMPLEMENTATION"]
    assert "firstNumber" in impl
    assert "secondNumber" in impl
    # Must NOT contain abbreviations
    for abbrev in ["n1", "n2", "num1", "num2", " a,", " b,", " x,", " y,"]:
        assert abbrev not in impl


def test_python_uses_snake_case():
    """Python output must use snake_case for functions."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("write add function", language="python")
    impl = result.sections["IMPLEMENTATION"]
    assert "def " in impl  # Python function definition
    # Should not have camelCase function names
    assert "addTotal" not in impl or "add_total" in impl


def test_javascript_uses_camel_case():
    """JavaScript output must use camelCase for functions."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("write add function", language="javascript")
    impl = result.sections["IMPLEMENTATION"]
    assert "const " in impl or "function " in impl
```

### 5. Observability Tests
Verify that logging and tracing work correctly.

```python
# test_observability.py

def test_llm_call_is_logged(caplog):
    """Every LLM call must produce a structured log entry."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    agent.generate("write add function")
    # Assert log contains required fields
    assert any("llm_call" in record.message for record in caplog.records)


def test_prompt_hash_is_logged(caplog):
    """Every user prompt must log its SHA-256 hash."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    agent.generate("write add function")
    expected_hash = hashlib.sha256("write add function".encode()).hexdigest()
    assert any(expected_hash[:16] in record.message for record in caplog.records)


def test_latency_is_recorded():
    """LLM call latency must be measured and logged."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    agent.generate("write add function")
    # Assert latency_ms is present in logs
    pass


def test_token_usage_is_recorded():
    """Token usage (prompt + completion) must be logged."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    agent.generate("write add function")
    # Assert tokens_in and tokens_out are present in logs
    pass
```

### 6. Edge Case Tests

```python
# test_edge_cases.py

def test_empty_intent_triggers_ambiguity():
    """Empty or whitespace-only intent must trigger AMBIGUITY."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("")
    assert result.is_ambiguity


def test_multi_function_request_is_split():
    """Requests for multiple functions must be split and processed independently."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    # "add two numbers and check if even" = 2 intents
    # Each should produce its own output block
    pass


def test_spec_file_skips_synonym_normalization():
    """YAML spec input bypasses synonym collapse (D-1)."""
    spec = """
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
    """
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate(spec)
    assert not result.is_ambiguity


def test_unsupported_language_triggers_ambiguity():
    """Requesting an unsupported language must trigger AMBIGUITY."""
    agent = DeterministicCodeAgent(api_key=API_KEY)
    result = agent.generate("write add function", language="brainfuck")
    assert result.is_ambiguity
```

## Running Tests

```bash
# Full test suite
python -m pytest tests/ -v

# Determinism tests only
python -m pytest tests/test_determinism.py -v

# Schema tests only
python -m pytest tests/test_schema.py -v

# Classification tests (parametrized)
python -m pytest tests/test_classification.py -v

# With coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing

# Deterministic hash seed (validates no hash-dependent behavior)
PYTHONHASHSEED=0 python -m pytest tests/ -v

# Run 5x regression check (CI gate)
for i in $(seq 1 5); do python -m pytest tests/test_determinism.py -v; done
```

## CI Integration

```yaml
# .github/workflows/determinism.yml
name: Determinism Gate
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov

      # Run full test suite
      - run: PYTHONHASHSEED=0 python -m pytest tests/ -v --cov=src

      # Determinism regression: run 5x, all hashes must match
      - name: Determinism regression
        run: |
          for i in 1 2 3 4 5; do
            python -m pytest tests/test_determinism.py -v || exit 1
          done
```

## Test Naming Convention

All test functions follow: `test_<what>_<expected_behavior>`

Examples:
- `test_identical_output_across_runs` — not `test_determinism_1`
- `test_synonym_produces_same_hash` — not `test_synonym`
- `test_max_retries_raises_value_error` — not `test_error`
