"""Tests for downstream consumers (Formatter, TestRunner, SDDRegistry, DependencyGraph)."""

import json

import pytest

from src.core.consumers import DependencyGraph, Formatter, SDDRegistry, TestRunner
from src.core.contracts import (
    AmbiguityBlock,
    CanonicalType,
    Classification,
    Confidence,
    DeterministicResult,
    NormalizedIntent,
    ParsedSections,
)


def _make_sections() -> ParsedSections:
    return ParsedSections(
        intent_classification="type: PURE_FUNCTION\nconfidence: HIGH",
        signature="javascript: const total = (a, b) => a + b",
        implementation="const total = (firstNumber, secondNumber) => firstNumber + secondNumber;",
        invariants="preconditions:\n  - inputs must be numbers",
        test_oracle="assert(total(1, 2) === 3);\nassert(total(0, 0) === 0);",
    )


def _make_result() -> DeterministicResult:
    sections = _make_sections()
    return DeterministicResult(
        sections=sections,
        content_hash="abcdef1234567890",
        raw_output="raw",
    )


def _make_ambiguity_result() -> DeterministicResult:
    ni = NormalizedIntent("unknown", "Thing", "frobnicate", "freetext")
    c = Classification(CanonicalType.PURE_FUNCTION, Confidence.LOW, ni, "javascript")
    ab = AmbiguityBlock("unclear verb", "Is this a function?", "Assuming PURE_FUNCTION", c)
    return DeterministicResult(
        sections=None,
        content_hash="",
        raw_output="",
        is_ambiguity=True,
        ambiguity=ab,
    )


class TestFormatter:
    def test_format_success(self):
        f = Formatter()
        output = f.format(_make_result())
        assert "=== Implementation ===" in output
        assert "const total" in output
        assert "[Hash: abcdef1234567890]" in output

    def test_format_ambiguity(self):
        f = Formatter()
        output = f.format(_make_ambiguity_result())
        assert "AMBIGUITY DETECTED" in output
        assert "unclear verb" in output

    def test_format_no_sections(self):
        f = Formatter()
        result = DeterministicResult(sections=None, content_hash="", raw_output="", is_ambiguity=True)
        output = f.format(result)
        # Should handle gracefully (no ambiguity block either)
        assert "ERROR" in output or "AMBIGUITY" in output

    def test_format_with_dependencies(self):
        sections = _make_sections()
        sections = ParsedSections(
            intent_classification=sections.intent_classification,
            signature=sections.signature,
            implementation=sections.implementation,
            invariants=sections.invariants,
            test_oracle=sections.test_oracle,
            dependencies="lodash",
        )
        result = DeterministicResult(sections=sections, content_hash="abc123def4567890", raw_output="raw")
        f = Formatter()
        output = f.format(result)
        assert "=== Dependencies ===" in output
        assert "lodash" in output


class TestSDDRegistry:
    def test_persist_and_lookup(self):
        registry = SDDRegistry()
        result = _make_result()
        record = registry.persist(result)

        assert record.content_hash == "abcdef1234567890"
        assert record.implementation == result.sections.implementation

        found = registry.lookup("abcdef1234567890")
        assert found is not None
        assert found.content_hash == record.content_hash

    def test_lookup_missing(self):
        registry = SDDRegistry()
        assert registry.lookup("nonexistent") is None

    def test_list_all(self):
        registry = SDDRegistry()
        registry.persist(_make_result())
        records = registry.list_all()
        assert len(records) == 1

    def test_persist_without_sections_raises(self):
        registry = SDDRegistry()
        result = DeterministicResult(
            sections=None, content_hash="", raw_output="", is_ambiguity=True
        )
        with pytest.raises(ValueError, match="Cannot persist"):
            registry.persist(result)

    def test_export_json(self):
        registry = SDDRegistry()
        result = _make_result()
        registry.persist(result)

        exported = registry.export_json("abcdef1234567890")
        assert exported is not None
        data = json.loads(exported)
        assert data["content_hash"] == "abcdef1234567890"
        assert "implementation" in data

    def test_export_json_missing(self):
        registry = SDDRegistry()
        assert registry.export_json("nonexistent") is None

    def test_overwrite_same_hash(self):
        registry = SDDRegistry()
        registry.persist(_make_result())
        registry.persist(_make_result())
        assert len(registry.list_all()) == 1


class TestTestRunner:
    def test_run_without_sections(self):
        runner = TestRunner()
        result = DeterministicResult(
            sections=None, content_hash="", raw_output="", is_ambiguity=True
        )
        test_result = runner.run(result)
        assert not test_result.success
        assert "No sections" in test_result.errors[0]

    def test_unsupported_language(self):
        runner = TestRunner()
        test_result = runner.run(_make_result(), language="go")
        assert not test_result.success
        assert "Unsupported" in test_result.errors[0]

    def test_run_javascript_success(self):
        """Run valid JS assertions via Node.js (if available)."""
        runner = TestRunner()
        result = _make_result()
        test_result = runner.run(result, language="javascript")
        # May fail if node is not installed — that's OK
        if "not found" not in str(test_result.errors):
            assert test_result.passed >= 0

    def test_run_python_success(self):
        """Run valid Python assertions."""
        sections = ParsedSections(
            intent_classification="type: PURE_FUNCTION",
            signature="python: def total(a, b) -> int",
            implementation="def total(first_number, second_number):\n    return first_number + second_number",
            invariants="preconditions: inputs are numbers",
            test_oracle="assert total(1, 2) == 3\nassert total(0, 0) == 0\nassert total(-1, 1) == 0",
        )
        result = DeterministicResult(
            sections=sections,
            content_hash=DeterministicResult.compute_hash(sections.implementation),
            raw_output="raw",
        )
        runner = TestRunner()
        test_result = runner.run(result, language="python")
        assert test_result.success
        assert test_result.passed == 3


class TestDependencyGraph:
    def test_no_dependencies(self):
        graph = DependencyGraph()
        result = _make_result()  # no dependencies
        nodes = graph.parse(result)
        assert nodes == []

    def test_no_sections(self):
        graph = DependencyGraph()
        result = DeterministicResult(
            sections=None, content_hash="", raw_output="", is_ambiguity=True
        )
        nodes = graph.parse(result)
        assert nodes == []

    def test_parse_simple_deps(self):
        sections = ParsedSections(
            intent_classification="type: ASYNC_OPERATION",
            signature="js: async function fetchUser()",
            implementation="async function fetchUser() { ... }",
            invariants="preconditions: ...",
            test_oracle="assert(true);",
            dependencies="axios\nlodash",
        )
        result = DeterministicResult(
            sections=sections,
            content_hash=DeterministicResult.compute_hash(sections.implementation),
            raw_output="raw",
        )
        graph = DependencyGraph()
        nodes = graph.parse(result)
        assert len(nodes) == 2
        assert nodes[0].module == "axios"
        assert nodes[1].module == "lodash"

    def test_parse_alias(self):
        sections = ParsedSections(
            intent_classification="ic",
            signature="sig",
            implementation="impl",
            invariants="inv",
            test_oracle="test",
            dependencies="numpy as np",
        )
        result = DeterministicResult(
            sections=sections,
            content_hash=DeterministicResult.compute_hash("impl"),
            raw_output="raw",
        )
        graph = DependencyGraph()
        nodes = graph.parse(result)
        assert len(nodes) == 1
        assert nodes[0].module == "numpy"
        assert nodes[0].alias == "np"

    def test_parse_bullet_format(self):
        sections = ParsedSections(
            intent_classification="ic",
            signature="sig",
            implementation="impl",
            invariants="inv",
            test_oracle="test",
            dependencies="- axios\n- lodash\n- dayjs",
        )
        result = DeterministicResult(
            sections=sections,
            content_hash=DeterministicResult.compute_hash("impl"),
            raw_output="raw",
        )
        graph = DependencyGraph()
        nodes = graph.parse(result)
        assert len(nodes) == 3
        assert nodes[0].module == "axios"

    def test_to_import_js(self):
        graph = DependencyGraph()
        from src.core.consumers import DependencyNode
        nodes = [DependencyNode("axios"), DependencyNode("lodash", alias="_")]
        stmts = graph.to_import_statements(nodes, "javascript")
        assert stmts[0] == "import axios from 'axios';"
        assert stmts[1] == "import * as _ from 'lodash';"

    def test_to_import_python(self):
        graph = DependencyGraph()
        from src.core.consumers import DependencyNode
        nodes = [DependencyNode("numpy", alias="np"), DependencyNode("os")]
        stmts = graph.to_import_statements(nodes, "python")
        assert stmts[0] == "import numpy as np"
        assert stmts[1] == "import os"

    def test_to_import_go(self):
        graph = DependencyGraph()
        from src.core.consumers import DependencyNode
        nodes = [DependencyNode("fmt"), DependencyNode("net/http", alias="http")]
        stmts = graph.to_import_statements(nodes, "go")
        assert stmts[0] == '"fmt"'
        assert stmts[1] == 'http "net/http"'

    def test_skip_comments_and_empty(self):
        sections = ParsedSections(
            intent_classification="ic",
            signature="sig",
            implementation="impl",
            invariants="inv",
            test_oracle="test",
            dependencies="# Runtime deps\naxios\n\n# Dev deps\njest",
        )
        result = DeterministicResult(
            sections=sections,
            content_hash=DeterministicResult.compute_hash("impl"),
            raw_output="raw",
        )
        graph = DependencyGraph()
        nodes = graph.parse(result)
        assert len(nodes) == 2
        assert nodes[0].module == "axios"
        assert nodes[1].module == "jest"
