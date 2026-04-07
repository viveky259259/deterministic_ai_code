# DetermBot Spec Index

> Spec-Driven Development manifest. Every component and feature is defined
> here before implementation begins. Build order follows the dependency graph.

## Build Order (bottom-up)

### Phase 1 — Data Contracts (no dependencies)
| Spec | File | Description |
|------|------|-------------|
| CanonicalType | `contracts/canonical_type.yaml` | 7-value enum of intent types |
| Confidence | `contracts/confidence.yaml` | HIGH / MEDIUM / LOW classification confidence |
| NormalizedIntent | `contracts/normalized_intent.yaml` | Canonical verb+noun after synonym collapse |
| Classification | `contracts/classification.yaml` | Intent type + confidence + language |
| AmbiguityBlock | `contracts/ambiguity_block.yaml` | Halt payload when confidence < HIGH |
| BoundPrompt | `contracts/bound_prompt.yaml` | System prompt + user message for API call |
| ParsedSections | `contracts/parsed_sections.yaml` | Validated output sections from Claude |
| DeterministicResult | `contracts/deterministic_result.yaml` | Final pipeline output with content hash |

### Phase 2 — Pipeline Components (depend on contracts)
| Spec | File | Layer | Depends On |
|------|------|-------|------------|
| IntentNormalizer | `components/intent_normalizer.yaml` | L1 | NormalizedIntent |
| CanonicalClassifier | `components/canonical_classifier.yaml` | L2 | NormalizedIntent, Classification, CanonicalType, Confidence |
| AmbiguityGate | `components/ambiguity_gate.yaml` | gate | Classification, AmbiguityBlock |
| SpecValidator | `components/spec_validator.yaml` | bypass | Classification, NormalizedIntent, CanonicalType |
| TemplateBinder | `components/template_binder.yaml` | L3 | Classification, BoundPrompt |
| ClaudeAPIAdapter | `components/claude_api_adapter.yaml` | L4 | BoundPrompt |
| SchemaParser | `components/schema_parser.yaml` | L5 | ParsedSections |
| DriftDetector | `components/drift_detector.yaml` | L5 | DeterministicResult |
| RetryOrchestrator | `components/retry_orchestrator.yaml` | ctrl | ClaudeAPIAdapter, SchemaParser, DriftDetector |

### Phase 3 — Features (depend on components)
| ID | Spec | File | Priority | Category |
|----|------|------|----------|----------|
| F-01 | Free-text input | `features/f01_freetext_input.yaml` | P0 | INPUT |
| F-02 | YAML/JSON spec input | `features/f02_spec_input.yaml` | P0 | INPUT |
| F-03 | Multi-language targeting | `features/f03_multi_language.yaml` | P0 | INPUT |
| F-04 | Multi-function decomposition | `features/f04_multi_function.yaml` | P1 | INPUT |
| F-05 | Synonym collapse | `features/f05_synonym_collapse.yaml` | P0 | NORMALISATION |
| F-06 | Canonical classifier | `features/f06_canonical_classifier.yaml` | P0 | NORMALISATION |
| F-07 | Ambiguity gate | `features/f07_ambiguity_gate.yaml` | P0 | NORMALISATION |
| F-08 | Naming enforcer | `features/f08_naming_enforcer.yaml` | P0 | NORMALISATION |
| F-09 | Template binder | `features/f09_template_binder.yaml` | P0 | GENERATION |
| F-10 | Structured output | `features/f10_structured_output.yaml` | P0 | GENERATION |
| F-11 | Invariant generation | `features/f11_invariant_generation.yaml` | P0 | GENERATION |
| F-12 | Test oracle generation | `features/f12_test_oracle.yaml` | P0 | GENERATION |
| F-13 | Schema parser | `features/f13_schema_parser.yaml` | P0 | VALIDATION |
| F-14 | Drift detector | `features/f14_drift_detector.yaml` | P0 | VALIDATION |
| F-15 | Retry harness | `features/f15_retry_harness.yaml` | P0 | VALIDATION |
| F-16 | Temperature lock | `features/f16_temperature_lock.yaml` | P0 | DETERMINISM |
| F-17 | Idempotent regeneration | `features/f17_idempotent_regeneration.yaml` | P0 | DETERMINISM |
| F-18 | Regression suite | `features/f18_regression_suite.yaml` | P0 | DETERMINISM |
| F-19 | New intent type protocol | `features/f19_new_intent_type.yaml` | P1 | EXTENSION |
| F-20 | New language target | `features/f20_new_language.yaml` | P1 | EXTENSION |
| F-21 | Downstream consumer API | `features/f21_downstream_consumer.yaml` | P1 | EXTENSION |

## Dependency Graph

```
Phase 1: Contracts (independent — build all in parallel)
  CanonicalType ─┐
  Confidence ────┤
  NormalizedIntent ──────────────────────┐
  Classification ──┬─────────────────────┤
  AmbiguityBlock ──┤                     │
  BoundPrompt ─────┤                     │
  ParsedSections ──┤                     │
  DeterministicResult ─┘                 │
                                         │
Phase 2: Components (depend on Phase 1)  │
  IntentNormalizer ◄─────────────────────┘
        │
        ▼
  CanonicalClassifier
        │
        ▼
  AmbiguityGate ──────► (halt path)
        │
        ▼
  SpecValidator ──────► (bypass path, joins at TemplateBinder)
        │
        ▼
  TemplateBinder
        │
        ▼
  ClaudeAPIAdapter
        │
        ▼
  SchemaParser ───────► RetryOrchestrator (loops back to ClaudeAPIAdapter)
        │
        ▼
  DriftDetector
        │
        ▼
  DeterministicResult (output)

Phase 3: Features (integration tests against assembled pipeline)
  P0 features first, P1 features after P0 passes
```

## Implementation Priority

**P0 — Must have for MVP:**
- All 8 contracts
- All 9 components
- F-01 through F-18 (input, normalisation, generation, validation, determinism)

**P1 — Post-MVP:**
- F-04 (multi-function decomposition)
- F-19 (new intent type protocol)
- F-20 (new language target)
- F-21 (downstream consumer API)

## Spec File Format

All specs use YAML with these top-level keys:
- `spec`: type (`contract` | `component` | `feature`)
- `name`: human-readable name
- `version`: semver
- `description`: what it does and why
- `acceptance_criteria` / `acceptance_tests`: how to verify it works
- `components_involved`: which components implement this spec
- `invariants`: what must always be true
