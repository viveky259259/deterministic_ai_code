"""L5 — Parses raw Claude API output into typed ParsedSections."""

from __future__ import annotations

import re
from typing import Optional

from src.core.contracts import ParsedSections
from src.logging.structured_logger import get_logger

logger = get_logger("core.schema_parser")

REQUIRED_SECTIONS = [
    "INTENT_CLASSIFICATION",
    "SIGNATURE",
    "IMPLEMENTATION",
    "INVARIANTS",
    "TEST_ORACLE",
]

_SECTION_PATTERN = re.compile(r"---(\w+)---(.*?)(?=---|\Z)", re.DOTALL)
_FENCE_PATTERN = re.compile(r"```\w*\n?")
_IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+", re.MULTILINE),
    re.compile(r"^\s*from\s+\S+\s+import\s+", re.MULTILINE),
    re.compile(r"^\s*require\s*\(", re.MULTILINE),
]


class SchemaParser:
    """Validates and parses raw Claude output into typed sections."""

    def parse(self, raw_output: str) -> Optional[ParsedSections]:
        """Parse raw output into validated sections. Returns None on failure."""
        if "---AMBIGUITY---" in raw_output:
            logger.info("ambiguity_detected")
            return None  # Caller handles ambiguity separately

        sections = self._extract_sections(raw_output)
        if sections is None:
            return None

        # Validate all required sections present
        for name in REQUIRED_SECTIONS:
            if name not in sections:
                logger.warning("missing_section", section=name)
                return None

        # Extract and validate implementation code
        code = self._extract_implementation_code(sections["IMPLEMENTATION"])
        if code is None:
            logger.warning("invalid_implementation_block")
            return None

        if not self._validate_implementation(code):
            return None

        return ParsedSections(
            intent_classification=sections["INTENT_CLASSIFICATION"],
            signature=sections["SIGNATURE"],
            implementation=code,
            invariants=sections["INVARIANTS"],
            test_oracle=sections["TEST_ORACLE"],
            dependencies=sections.get("DEPENDENCIES"),
        )

    def _extract_sections(self, raw: str) -> dict[str, str] | None:
        """Regex-extract all sections from raw output."""
        matches = _SECTION_PATTERN.findall(raw)
        if not matches:
            logger.warning("no_sections_found")
            return None

        sections: dict[str, str] = {}
        for name, content in matches:
            sections[name] = content.strip()
        return sections

    def _extract_implementation_code(self, raw_impl: str) -> str | None:
        """Strip fences and language tag from implementation block."""
        # Check that there's at least one fenced code block
        fence_count = raw_impl.count("```")
        if fence_count < 2:
            return None
        if fence_count > 2:
            logger.warning("multiple_code_blocks_in_implementation")
            return None

        code = _FENCE_PATTERN.sub("", raw_impl).strip()
        if not code:
            return None
        return code

    def _validate_implementation(self, code: str) -> bool:
        """Validate implementation block constraints."""
        for pattern in _IMPORT_PATTERNS:
            if pattern.search(code):
                logger.warning("import_in_implementation")
                return False
        return True

    def is_ambiguity(self, raw_output: str) -> bool:
        """Check if raw output contains an AMBIGUITY section."""
        return "---AMBIGUITY---" in raw_output
