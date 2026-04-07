"""F-21 — Downstream consumers of DeterministicResult."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.contracts import DeterministicResult, ParsedSections
from src.logging.structured_logger import get_logger

logger = get_logger("core.consumers")


class Formatter:
    """Transforms ParsedSections into a formatted string for display."""

    def format(self, result: DeterministicResult) -> str:
        """Format a DeterministicResult for human-readable output."""
        if result.is_ambiguity and result.ambiguity:
            return (
                f"AMBIGUITY DETECTED\n"
                f"  Unclear: {result.ambiguity.unclear_dimension}\n"
                f"  Question: {result.ambiguity.clarifying_question}\n"
                f"  Assumed: {result.ambiguity.assumed_interpretation}"
            )

        if result.sections is None:
            return "ERROR: No sections available"

        s = result.sections
        lines = [
            f"=== Intent Classification ===\n{s.intent_classification}",
            f"\n=== Signature ===\n{s.signature}",
            f"\n=== Implementation ===\n{s.implementation}",
            f"\n=== Invariants ===\n{s.invariants}",
            f"\n=== Test Oracle ===\n{s.test_oracle}",
        ]
        if s.dependencies:
            lines.append(f"\n=== Dependencies ===\n{s.dependencies}")
        lines.append(f"\n[Hash: {result.content_hash}]")
        return "\n".join(lines)


@dataclass
class TestResult:
    """Result of running test oracle assertions."""

    passed: int
    failed: int
    errors: list[str]

    @property
    def success(self) -> bool:
        return self.failed == 0 and len(self.errors) == 0


class TestRunner:
    """Executes test oracle assertions and returns pass/fail."""

    def run(self, result: DeterministicResult, language: str = "javascript") -> TestResult:
        """Execute test assertions from the oracle section."""
        if result.sections is None:
            return TestResult(passed=0, failed=0, errors=["No sections available"])

        oracle = result.sections.test_oracle
        impl = result.sections.implementation

        if language == "javascript":
            return self._run_javascript(impl, oracle)
        elif language == "python":
            return self._run_python(impl, oracle)
        else:
            return TestResult(passed=0, failed=0, errors=[f"Unsupported language: {language}"])

    def _run_javascript(self, impl: str, oracle: str) -> TestResult:
        """Run JavaScript assertions via Node.js."""
        code = f"{impl}\n\n{oracle}"
        return self._execute_code(code, "node", ".js")

    def _run_python(self, impl: str, oracle: str) -> TestResult:
        """Run Python assertions."""
        code = f"{impl}\n\n{oracle}"
        return self._execute_code(code, "python3", ".py")

    def _execute_code(self, code: str, runtime: str, ext: str) -> TestResult:
        """Write code to temp file and execute."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=ext, delete=False
            ) as f:
                f.write(code)
                f.flush()
                path = f.name

            proc = subprocess.run(
                [runtime, path],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if proc.returncode == 0:
                # Count assert statements as passed
                assert_count = code.count("assert")
                logger.info("test_oracle_passed", assertions=assert_count)
                return TestResult(passed=assert_count, failed=0, errors=[])
            else:
                logger.warning("test_oracle_failed", stderr=proc.stderr[:500])
                return TestResult(
                    passed=0, failed=1, errors=[proc.stderr.strip()[:500]]
                )
        except FileNotFoundError:
            return TestResult(
                passed=0, failed=0, errors=[f"Runtime '{runtime}' not found"]
            )
        except subprocess.TimeoutExpired:
            return TestResult(passed=0, failed=0, errors=["Test execution timed out"])
        finally:
            Path(path).unlink(missing_ok=True)


@dataclass
class SDDRecord:
    """A persisted spec record in the SDD registry."""

    content_hash: str
    intent_classification: str
    signature: str
    implementation: str
    invariants: str
    test_oracle: str
    dependencies: Optional[str]


class SDDRegistry:
    """Persists DeterministicResults to a spec store, keyed by content_hash."""

    def __init__(self) -> None:
        self._store: dict[str, SDDRecord] = {}

    def persist(self, result: DeterministicResult) -> SDDRecord:
        """Persist a result to the registry. Returns the SDDRecord."""
        if result.sections is None:
            raise ValueError("Cannot persist result without sections")

        s = result.sections
        record = SDDRecord(
            content_hash=result.content_hash,
            intent_classification=s.intent_classification,
            signature=s.signature,
            implementation=s.implementation,
            invariants=s.invariants,
            test_oracle=s.test_oracle,
            dependencies=s.dependencies,
        )
        self._store[result.content_hash] = record
        logger.info("sdd_record_persisted", content_hash=result.content_hash)
        return record

    def lookup(self, content_hash: str) -> Optional[SDDRecord]:
        """Look up a record by content hash."""
        return self._store.get(content_hash)

    def list_all(self) -> list[SDDRecord]:
        """List all persisted records."""
        return list(self._store.values())

    def export_json(self, content_hash: str) -> Optional[str]:
        """Export a record as JSON."""
        record = self.lookup(content_hash)
        if record is None:
            return None
        return json.dumps({
            "content_hash": record.content_hash,
            "intent_classification": record.intent_classification,
            "signature": record.signature,
            "implementation": record.implementation,
            "invariants": record.invariants,
            "test_oracle": record.test_oracle,
            "dependencies": record.dependencies,
        }, indent=2)


@dataclass
class DependencyNode:
    """A single import dependency."""

    module: str
    alias: Optional[str] = None


class DependencyGraph:
    """Parses DEPENDENCIES section into an import graph."""

    def parse(self, result: DeterministicResult) -> list[DependencyNode]:
        """Extract dependency list from a DeterministicResult."""
        if result.sections is None or result.sections.dependencies is None:
            return []

        raw = result.sections.dependencies.strip()
        if not raw:
            return []

        nodes: list[DependencyNode] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            node = self._parse_line(line)
            if node:
                nodes.append(node)

        logger.info("dependencies_parsed", count=len(nodes))
        return nodes

    def _parse_line(self, line: str) -> Optional[DependencyNode]:
        """Parse a single dependency line."""
        line = line.strip().rstrip(",").strip()
        if not line:
            return None

        # Handle "module as alias" pattern
        if " as " in line:
            parts = line.split(" as ", 1)
            return DependencyNode(module=parts[0].strip(), alias=parts[1].strip())

        # Handle "- module" bullet point format
        if line.startswith("- "):
            line = line[2:].strip()

        return DependencyNode(module=line)

    def to_import_statements(
        self, nodes: list[DependencyNode], language: str = "javascript"
    ) -> list[str]:
        """Convert dependency nodes to import statements for target language."""
        statements: list[str] = []
        for node in nodes:
            if language in ("javascript", "typescript"):
                if node.alias:
                    statements.append(f"import * as {node.alias} from '{node.module}';")
                else:
                    statements.append(f"import {node.module} from '{node.module}';")
            elif language == "python":
                if node.alias:
                    statements.append(f"import {node.module} as {node.alias}")
                else:
                    statements.append(f"import {node.module}")
            elif language == "go":
                if node.alias:
                    statements.append(f'{node.alias} "{node.module}"')
                else:
                    statements.append(f'"{node.module}"')
        return statements
