"""Project-level spec parser for multi-function project generation.

Parses a YAML project spec into a structured ProjectSpec with modules,
function intents, and shared data contracts. This is the entry point
for Phase 1 of the Project Composer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import yaml

from src.logging.structured_logger import get_logger

logger = get_logger("core.project_spec")


@dataclass(frozen=True)
class FunctionSpec:
    """A single function intent within a module."""

    intent: str
    language: Optional[str] = None  # overrides module/project default


@dataclass(frozen=True)
class DataContractSpec:
    """A shared type definition used across modules."""

    name: str
    fields: dict[str, str]  # field_name → type_string
    description: str = ""


@dataclass(frozen=True)
class ModuleSpec:
    """A group of related functions forming a single file/module."""

    name: str
    functions: tuple[FunctionSpec, ...]
    description: str = ""


@dataclass(frozen=True)
class ProjectSpec:
    """Top-level project specification."""

    name: str
    language: str
    modules: tuple[ModuleSpec, ...]
    data_contracts: tuple[DataContractSpec, ...]
    description: str = ""


class ProjectSpecError(Exception):
    """Raised when a project spec is invalid."""


class ProjectSpecParser:
    """Parses YAML project specs into ProjectSpec objects."""

    SUPPORTED_LANGUAGES = frozenset({
        "javascript", "typescript", "python", "go",
        "js", "ts", "py", "golang",
    })

    def parse(self, spec_input: str) -> ProjectSpec:
        """Parse a YAML string into a ProjectSpec."""
        raw = self._load_yaml(spec_input)
        self._validate_top_level(raw)

        project = raw["project"]
        name = self._require_string(project, "name", "project")
        language = self._require_language(project)
        description = project.get("description", "")

        data_contracts = self._parse_data_contracts(project.get("data_contracts", []))
        modules = self._parse_modules(project.get("modules", []))

        if not modules and not data_contracts:
            raise ProjectSpecError(
                "Project must have at least one module or data_contract"
            )

        spec = ProjectSpec(
            name=name,
            language=language,
            modules=tuple(modules),
            data_contracts=tuple(data_contracts),
            description=description,
        )

        logger.info(
            "project_spec_parsed",
            project_name=name,
            language=language,
            module_count=len(modules),
            contract_count=len(data_contracts),
            function_count=sum(len(m.functions) for m in modules),
        )

        return spec

    def _load_yaml(self, spec_input: str) -> dict:
        """Parse YAML string into dict."""
        try:
            result = yaml.safe_load(spec_input.strip())
        except yaml.YAMLError as exc:
            raise ProjectSpecError(f"Invalid YAML: {exc}") from exc

        if not isinstance(result, dict):
            raise ProjectSpecError("Spec must be a YAML mapping")
        return result

    def _validate_top_level(self, raw: dict) -> None:
        """Ensure the top-level 'project' key exists."""
        if "project" not in raw:
            raise ProjectSpecError("Missing top-level 'project' key")
        if not isinstance(raw["project"], dict):
            raise ProjectSpecError("'project' must be a mapping")

    def _require_string(self, mapping: dict, key: str, context: str) -> str:
        """Extract a required string field."""
        if key not in mapping:
            raise ProjectSpecError(f"Missing required field '{key}' in {context}")
        value = mapping[key]
        if not isinstance(value, str) or not value.strip():
            raise ProjectSpecError(f"'{key}' must be a non-empty string in {context}")
        return value.strip()

    def _require_language(self, project: dict) -> str:
        """Extract and validate the project language."""
        language = self._require_string(project, "language", "project").lower()
        if language not in self.SUPPORTED_LANGUAGES:
            raise ProjectSpecError(
                f"Unsupported language: '{language}'. "
                f"Supported: {sorted(self.SUPPORTED_LANGUAGES)}"
            )
        return language

    def _parse_data_contracts(
        self, raw_contracts: list,
    ) -> list[DataContractSpec]:
        """Parse the data_contracts section."""
        if not isinstance(raw_contracts, list):
            raise ProjectSpecError("'data_contracts' must be a list")

        contracts: list[DataContractSpec] = []
        seen_names: set[str] = set()

        for idx, entry in enumerate(raw_contracts):
            if not isinstance(entry, dict):
                raise ProjectSpecError(
                    f"data_contracts[{idx}] must be a mapping"
                )

            name = self._require_string(entry, "name", f"data_contracts[{idx}]")

            if name in seen_names:
                raise ProjectSpecError(f"Duplicate data contract name: '{name}'")
            seen_names.add(name)

            raw_fields = entry.get("fields", {})
            if not isinstance(raw_fields, dict) or not raw_fields:
                raise ProjectSpecError(
                    f"data_contracts[{idx}] '{name}' must have non-empty 'fields' mapping"
                )

            fields = {
                str(field_name): str(field_type)
                for field_name, field_type in raw_fields.items()
            }
            description = entry.get("description", "")

            contracts.append(DataContractSpec(
                name=name,
                fields=fields,
                description=str(description),
            ))

        return contracts

    def _parse_modules(self, raw_modules: list) -> list[ModuleSpec]:
        """Parse the modules section."""
        if not isinstance(raw_modules, list):
            raise ProjectSpecError("'modules' must be a list")

        modules: list[ModuleSpec] = []
        seen_names: set[str] = set()

        for idx, entry in enumerate(raw_modules):
            if not isinstance(entry, dict):
                raise ProjectSpecError(f"modules[{idx}] must be a mapping")

            name = self._require_string(entry, "name", f"modules[{idx}]")

            if name in seen_names:
                raise ProjectSpecError(f"Duplicate module name: '{name}'")
            seen_names.add(name)

            raw_functions = entry.get("functions", [])
            if not isinstance(raw_functions, list) or not raw_functions:
                raise ProjectSpecError(
                    f"modules[{idx}] '{name}' must have non-empty 'functions' list"
                )

            functions = self._parse_functions(raw_functions, f"modules[{idx}]")
            description = entry.get("description", "")

            modules.append(ModuleSpec(
                name=name,
                functions=tuple(functions),
                description=str(description),
            ))

        return modules

    def _parse_functions(
        self, raw_functions: list, context: str,
    ) -> list[FunctionSpec]:
        """Parse function list — supports string shorthand or mapping."""
        functions: list[FunctionSpec] = []

        for idx, entry in enumerate(raw_functions):
            if isinstance(entry, str):
                functions.append(FunctionSpec(intent=entry.strip()))
            elif isinstance(entry, dict):
                intent = self._require_string(
                    entry, "intent", f"{context}.functions[{idx}]"
                )
                language = entry.get("language")
                if language is not None:
                    language = str(language).strip().lower()
                functions.append(FunctionSpec(intent=intent, language=language))
            else:
                raise ProjectSpecError(
                    f"{context}.functions[{idx}] must be a string or mapping"
                )

        return functions

    def build_order(self, spec: ProjectSpec) -> list[str]:
        """Return generation order: data_contracts first, then modules in order."""
        order: list[str] = []
        for contract in spec.data_contracts:
            order.append(f"contract:{contract.name}")
        for module in spec.modules:
            for func in module.functions:
                order.append(f"{module.name}:{func.intent}")
        return order

    def total_generation_count(self, spec: ProjectSpec) -> int:
        """Total number of items to generate (contracts + functions)."""
        function_count = sum(len(m.functions) for m in spec.modules)
        return len(spec.data_contracts) + function_count
