# Consumers

The `consumers.py` module contains downstream consumers of the `DeterministicResult`. These are classes that take the output of the pipeline and perform some action, such as formatting the output, running tests, or persisting the result.

## Class: `Formatter`

The `Formatter` class transforms a `DeterministicResult` into a human-readable string for display.

### `format(self, result: DeterministicResult) -> str`

This method takes a `DeterministicResult` and returns a formatted string containing all the sections of the result.

## Class: `TestRunner`

The `TestRunner` class executes the test oracle assertions from the `DeterministicResult` and returns a `TestResult` object.

### `run(self, result: DeterministicResult, language: str) -> TestResult`

This method runs the test assertions from the `test_oracle` section of the result. It supports multiple languages by writing the code to a temporary file and executing it with the appropriate runtime (e.g., `node` for JavaScript, `python3` for Python).

## Class: `SDDRegistry`

The `SDDRegistry` class persists `DeterministicResult` objects to a spec store, keyed by their content hash. This is part of the Spec-Driven Development (SDD) workflow.

### `persist(self, result: DeterministicResult) -> SDDRecord`

This method persists a result to the registry and returns an `SDDRecord`.

### `lookup(self, content_hash: str) -> Optional[SDDRecord]`

This method looks up a record by its content hash.

## Class: `DependencyGraph`

The `DependencyGraph` class parses the `DEPENDENCIES` section of a `DeterministicResult` and builds an import graph.

### `parse(self, result: DeterministicResult) -> list[DependencyNode]`

This method extracts a list of `DependencyNode` objects from the `dependencies` section of the result.

### `to_import_statements(self, nodes: list[DependencyNode], language: str) -> list[str]`

This method converts a list of `DependencyNode` objects into import statements for the target language.
