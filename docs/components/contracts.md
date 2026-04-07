# Contracts

The `contracts.py` module defines the data contracts for the DetermBot pipeline. These are typed data structures that flow between the different stages of the pipeline. The module contains enums, dataclasses, and type aliases, but no business logic.

## Enums

### `CanonicalType`

An enum representing the supported canonical intent types, such as `PURE_FUNCTION`, `PREDICATE`, `TRANSFORMER`, etc.

### `Confidence`

An enum representing the confidence level of a classification: `HIGH`, `MEDIUM`, or `LOW`.

## Dataclasses

### `NormalizedIntent`

The output of the `IntentNormalizer`. It contains the canonical verb and noun, the raw input, and the source of the input ("freetext", "yaml_spec", or "json_spec").

### `Classification`

The output of the `CanonicalClassifier`. It contains the `CanonicalType`, the `Confidence` level, the `NormalizedIntent`, and the target language.

### `AmbiguityBlock`

Returned by the `AmbiguityGate` when the classification confidence is less than `HIGH`. It contains information about the ambiguity and a clarifying question for the user.

### `BoundPrompt`

The output of the `TemplateBinder`. It contains the system prompt and user message that are ready to be sent to the Claude API.

### `ParsedSections`

Represents the validated sections extracted from the raw output of the Claude API. It includes the intent classification, signature, implementation, invariants, test oracle, and optional dependencies.

### `DeterministicResult`

The final output of the pipeline. It contains the `ParsedSections`, a content hash for drift detection, the raw output from the API, and an optional `AmbiguityBlock`.
