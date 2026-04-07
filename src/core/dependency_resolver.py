"""Phase 3 — Topological sort of project generation items.

Resolves the build order for a ProjectSpec by analyzing which functions
reference shared data contracts. Data contracts are always generated first,
and functions that reference contracts must be generated after them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.core.project_spec import DataContractSpec, ModuleSpec, ProjectSpec
from src.logging.structured_logger import get_logger

logger = get_logger("core.dependency_resolver")


@dataclass(frozen=True)
class GenerationItem:
    """A single item in the generation queue."""

    key: str  # unique identifier, e.g. "contract:User" or "auth:hashPassword"
    intent: str  # the intent string to feed to agent.generate()
    language: str  # target language
    module_name: Optional[str] = None  # None for data contracts
    depends_on: tuple[str, ...] = ()  # keys of items this depends on


class CyclicDependencyError(Exception):
    """Raised when the dependency graph contains a cycle."""


class DependencyResolver:
    """Resolves generation order from a ProjectSpec.

    Rules:
      1. Data contracts have no dependencies (always generated first).
      2. Functions may depend on data contracts if the contract name
         appears in the function's intent text.
      3. Functions within the same module are ordered as declared.
      4. The output is a deterministic topological sort.
    """

    def resolve(self, spec: ProjectSpec) -> list[GenerationItem]:
        """Build a topologically-sorted generation order."""
        contract_names = frozenset(c.name.lower() for c in spec.data_contracts)
        items: dict[str, GenerationItem] = {}
        graph: dict[str, list[str]] = {}

        # Phase 1: Register all data contracts (no dependencies)
        for contract in spec.data_contracts:
            key = f"contract:{contract.name}"
            intent = self._build_contract_intent(contract)
            items[key] = GenerationItem(
                key=key,
                intent=intent,
                language=spec.language,
                module_name=None,
                depends_on=(),
            )
            graph[key] = []

        # Phase 2: Register all functions with dependencies on contracts
        for module in spec.modules:
            for func in module.functions:
                key = f"{module.name}:{func.intent}"
                language = func.language or spec.language
                deps = self._detect_contract_deps(
                    func.intent, contract_names, spec.data_contracts
                )
                items[key] = GenerationItem(
                    key=key,
                    intent=func.intent,
                    language=language,
                    module_name=module.name,
                    depends_on=tuple(deps),
                )
                graph[key] = list(deps)

        # Phase 3: Topological sort
        sorted_keys = self._topological_sort(graph)

        result = [items[key] for key in sorted_keys]

        logger.info(
            "dependency_resolution_complete",
            total_items=len(result),
            contract_count=len(spec.data_contracts),
            function_count=len(result) - len(spec.data_contracts),
        )

        return result

    def _build_contract_intent(self, contract: DataContractSpec) -> str:
        """Build a generation intent for a data contract."""
        field_descriptions = ", ".join(
            f"{name}: {ftype}" for name, ftype in contract.fields.items()
        )
        intent = f"define {contract.name} type with fields {field_descriptions}"
        if contract.description:
            intent += f". {contract.description}"
        return intent

    def _detect_contract_deps(
        self,
        intent: str,
        contract_names: frozenset[str],
        contracts: tuple[DataContractSpec, ...],
    ) -> list[str]:
        """Detect which data contracts a function intent references."""
        intent_lower = intent.lower()
        deps: list[str] = []
        for contract in contracts:
            if contract.name.lower() in intent_lower:
                deps.append(f"contract:{contract.name}")
        return sorted(deps)  # deterministic order

    def _topological_sort(self, graph: dict[str, list[str]]) -> list[str]:
        """Kahn's algorithm for deterministic topological sort."""
        in_degree: dict[str, int] = {node: 0 for node in graph}
        for node in graph:
            for dep in graph[node]:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0)

        # Calculate actual in-degrees
        for node in graph:
            for dep in graph[node]:
                # dep is a dependency OF node, meaning dep must come before node
                # So node has in-degree from dep
                pass

        # Rebuild: in_degree[node] = number of nodes that must come before it
        in_degree = {node: 0 for node in graph}
        adjacency: dict[str, list[str]] = {node: [] for node in graph}
        for node, deps in graph.items():
            in_degree[node] = len(deps)
            for dep in deps:
                if dep in adjacency:
                    adjacency[dep].append(node)

        # Start with nodes that have no dependencies
        queue = sorted(
            [node for node, degree in in_degree.items() if degree == 0]
        )
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dependent in sorted(adjacency.get(node, [])):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
            queue.sort()  # deterministic ordering

        if len(result) != len(graph):
            missing = set(graph.keys()) - set(result)
            raise CyclicDependencyError(
                f"Cyclic dependency detected involving: {sorted(missing)}"
            )

        return result
