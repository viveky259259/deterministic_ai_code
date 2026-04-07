"""Tests for DependencyResolver — topological sort of generation items."""

import pytest

from src.core.dependency_resolver import (
    DependencyResolver,
    GenerationItem,
)
from src.core.project_spec import (
    DataContractSpec,
    FunctionSpec,
    ModuleSpec,
    ProjectSpec,
)


@pytest.fixture
def resolver():
    return DependencyResolver()


def _make_spec(
    modules: list[ModuleSpec] | None = None,
    contracts: list[DataContractSpec] | None = None,
    language: str = "typescript",
) -> ProjectSpec:
    return ProjectSpec(
        name="test-project",
        language=language,
        modules=tuple(modules or []),
        data_contracts=tuple(contracts or []),
    )


# ── Basic Resolution ──────────────────────────────────────────────────────────


class TestBasicResolution:
    def test_empty_project(self, resolver):
        spec = _make_spec()
        result = resolver.resolve(spec)
        assert result == []

    def test_contracts_only(self, resolver):
        spec = _make_spec(contracts=[
            DataContractSpec("User", {"id": "string", "email": "string"}),
            DataContractSpec("AuthToken", {"token": "string"}),
        ])
        result = resolver.resolve(spec)
        assert len(result) == 2
        assert result[0].key == "contract:AuthToken"  # alphabetical
        assert result[1].key == "contract:User"

    def test_functions_only(self, resolver):
        spec = _make_spec(modules=[
            ModuleSpec("auth", (
                FunctionSpec("hash password"),
                FunctionSpec("verify password"),
            )),
        ])
        result = resolver.resolve(spec)
        assert len(result) == 2
        keys = [item.key for item in result]
        assert "auth:hash password" in keys
        assert "auth:verify password" in keys

    def test_contracts_before_functions(self, resolver):
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
            ],
            modules=[
                ModuleSpec("auth", (
                    FunctionSpec("create User in database"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        assert len(result) == 2
        assert result[0].key == "contract:User"
        assert result[1].key == "auth:create User in database"


# ── Dependency Detection ──────────────────────────────────────────────────────


class TestDependencyDetection:
    def test_function_depends_on_contract(self, resolver):
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
            ],
            modules=[
                ModuleSpec("user", (
                    FunctionSpec("fetch User by id"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        func_item = [r for r in result if r.key == "user:fetch User by id"][0]
        assert "contract:User" in func_item.depends_on

    def test_function_no_contract_dependency(self, resolver):
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
            ],
            modules=[
                ModuleSpec("math", (
                    FunctionSpec("add two numbers"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        func_item = [r for r in result if r.key == "math:add two numbers"][0]
        assert func_item.depends_on == ()

    def test_function_depends_on_multiple_contracts(self, resolver):
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
                DataContractSpec("AuthToken", {"token": "string"}),
            ],
            modules=[
                ModuleSpec("auth", (
                    FunctionSpec("create AuthToken for User"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        func_item = [r for r in result if r.key == "auth:create AuthToken for User"][0]
        assert "contract:AuthToken" in func_item.depends_on
        assert "contract:User" in func_item.depends_on

    def test_case_insensitive_detection(self, resolver):
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
            ],
            modules=[
                ModuleSpec("user", (
                    FunctionSpec("fetch user by id"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        func_item = [r for r in result if r.key == "user:fetch user by id"][0]
        assert "contract:User" in func_item.depends_on


# ── Ordering Guarantees ───────────────────────────────────────────────────────


class TestOrderingGuarantees:
    def test_deterministic_order(self, resolver):
        """Same input always produces same order."""
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
                DataContractSpec("AuthToken", {"token": "string"}),
            ],
            modules=[
                ModuleSpec("auth", (
                    FunctionSpec("hash password"),
                    FunctionSpec("create AuthToken for User"),
                )),
                ModuleSpec("user", (
                    FunctionSpec("fetch User by id"),
                )),
            ],
        )
        order1 = [item.key for item in resolver.resolve(spec)]
        order2 = [item.key for item in resolver.resolve(spec)]
        assert order1 == order2

    def test_all_contracts_before_dependent_functions(self, resolver):
        spec = _make_spec(
            contracts=[
                DataContractSpec("User", {"id": "string"}),
                DataContractSpec("AuthToken", {"token": "string"}),
            ],
            modules=[
                ModuleSpec("auth", (
                    FunctionSpec("create AuthToken for User"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        keys = [item.key for item in result]

        func_idx = keys.index("auth:create AuthToken for User")
        user_idx = keys.index("contract:User")
        token_idx = keys.index("contract:AuthToken")

        assert user_idx < func_idx
        assert token_idx < func_idx

    def test_independent_functions_sorted_alphabetically(self, resolver):
        """Functions with no dependencies are sorted for determinism."""
        spec = _make_spec(
            modules=[
                ModuleSpec("math", (
                    FunctionSpec("subtract numbers"),
                    FunctionSpec("add numbers"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        keys = [item.key for item in result]
        assert keys == sorted(keys)


# ── Generation Item Properties ────────────────────────────────────────────────


class TestGenerationItemProperties:
    def test_contract_item_has_no_module(self, resolver):
        spec = _make_spec(contracts=[
            DataContractSpec("User", {"id": "string", "email": "string"}),
        ])
        result = resolver.resolve(spec)
        assert result[0].module_name is None

    def test_function_item_has_module(self, resolver):
        spec = _make_spec(modules=[
            ModuleSpec("auth", (FunctionSpec("hash password"),)),
        ])
        result = resolver.resolve(spec)
        assert result[0].module_name == "auth"

    def test_contract_intent_includes_fields(self, resolver):
        spec = _make_spec(contracts=[
            DataContractSpec(
                "User",
                {"id": "string", "email": "string"},
                description="Core user entity",
            ),
        ])
        result = resolver.resolve(spec)
        assert "id: string" in result[0].intent
        assert "email: string" in result[0].intent
        assert "Core user entity" in result[0].intent

    def test_function_language_override(self, resolver):
        spec = _make_spec(
            language="typescript",
            modules=[
                ModuleSpec("data", (
                    FunctionSpec("process data", language="python"),
                    FunctionSpec("validate data"),
                )),
            ],
        )
        result = resolver.resolve(spec)
        items_by_key = {item.key: item for item in result}
        assert items_by_key["data:process data"].language == "python"
        assert items_by_key["data:validate data"].language == "typescript"

    def test_contract_uses_project_language(self, resolver):
        spec = _make_spec(
            language="go",
            contracts=[DataContractSpec("User", {"id": "string"})],
        )
        result = resolver.resolve(spec)
        assert result[0].language == "go"


# ── Full Project ──────────────────────────────────────────────────────────────


class TestFullProject:
    def test_auth_service_order(self, resolver):
        spec = ProjectSpec(
            name="user-auth-service",
            language="typescript",
            data_contracts=(
                DataContractSpec("User", {"id": "string", "email": "string"}),
                DataContractSpec("AuthToken", {"token": "string", "userId": "string"}),
            ),
            modules=(
                ModuleSpec("validation", (
                    FunctionSpec("validate email format"),
                    FunctionSpec("check if User exists"),
                )),
                ModuleSpec("auth", (
                    FunctionSpec("hash password"),
                    FunctionSpec("generate AuthToken for User"),
                )),
                ModuleSpec("user", (
                    FunctionSpec("create User in database"),
                    FunctionSpec("fetch User by id"),
                )),
            ),
        )
        result = resolver.resolve(spec)
        keys = [item.key for item in result]

        # Contracts must come before any function referencing them
        assert keys.index("contract:User") < keys.index("validation:check if User exists")
        assert keys.index("contract:User") < keys.index("auth:generate AuthToken for User")
        assert keys.index("contract:AuthToken") < keys.index("auth:generate AuthToken for User")
        assert keys.index("contract:User") < keys.index("user:create User in database")
        assert keys.index("contract:User") < keys.index("user:fetch User by id")

        # Independent functions (hash password, validate email) have no contract deps
        hash_item = [r for r in result if r.key == "auth:hash password"][0]
        assert hash_item.depends_on == ()

        email_item = [r for r in result if r.key == "validation:validate email format"][0]
        assert email_item.depends_on == ()

    def test_total_items(self, resolver):
        spec = ProjectSpec(
            name="test",
            language="typescript",
            data_contracts=(
                DataContractSpec("User", {"id": "string"}),
            ),
            modules=(
                ModuleSpec("mod", (
                    FunctionSpec("do something"),
                    FunctionSpec("do other thing"),
                )),
            ),
        )
        result = resolver.resolve(spec)
        assert len(result) == 3  # 1 contract + 2 functions
