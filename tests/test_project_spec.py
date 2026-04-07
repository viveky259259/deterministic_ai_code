"""Tests for ProjectSpecParser."""

import pytest

from src.core.project_spec import (
    DataContractSpec,
    FunctionSpec,
    ModuleSpec,
    ProjectSpec,
    ProjectSpecError,
    ProjectSpecParser,
)


@pytest.fixture
def parser():
    return ProjectSpecParser()


MINIMAL_SPEC = """
project:
  name: my-app
  language: typescript
  modules:
    - name: auth
      functions:
        - hash password
"""

FULL_SPEC = """
project:
  name: user-auth-service
  language: typescript
  description: A user authentication service

  data_contracts:
    - name: User
      description: Core user entity
      fields:
        id: string
        email: string
        createdAt: Date

    - name: AuthToken
      fields:
        token: string
        expiresAt: Date
        userId: string

  modules:
    - name: validation
      description: Input validation predicates
      functions:
        - validate email format
        - validate password strength
        - check if user exists

    - name: auth
      functions:
        - hash password
        - verify password hash
        - generate auth token

    - name: user
      functions:
        - intent: create user in database
          language: python
        - fetch user by id
        - update user profile
"""

CONTRACTS_ONLY_SPEC = """
project:
  name: shared-types
  language: typescript
  data_contracts:
    - name: User
      fields:
        id: string
        name: string
"""


class TestValidSpecs:
    def test_minimal_spec(self, parser):
        spec = parser.parse(MINIMAL_SPEC)
        assert spec.name == "my-app"
        assert spec.language == "typescript"
        assert len(spec.modules) == 1
        assert spec.modules[0].name == "auth"
        assert len(spec.modules[0].functions) == 1
        assert spec.modules[0].functions[0].intent == "hash password"

    def test_full_spec_structure(self, parser):
        spec = parser.parse(FULL_SPEC)
        assert spec.name == "user-auth-service"
        assert spec.language == "typescript"
        assert spec.description == "A user authentication service"

    def test_full_spec_contracts(self, parser):
        spec = parser.parse(FULL_SPEC)
        assert len(spec.data_contracts) == 2
        assert spec.data_contracts[0].name == "User"
        assert spec.data_contracts[0].fields["email"] == "string"
        assert spec.data_contracts[1].name == "AuthToken"

    def test_full_spec_modules(self, parser):
        spec = parser.parse(FULL_SPEC)
        assert len(spec.modules) == 3
        assert spec.modules[0].name == "validation"
        assert len(spec.modules[0].functions) == 3
        assert spec.modules[1].name == "auth"
        assert len(spec.modules[1].functions) == 3
        assert spec.modules[2].name == "user"
        assert len(spec.modules[2].functions) == 3

    def test_function_string_shorthand(self, parser):
        spec = parser.parse(FULL_SPEC)
        func = spec.modules[0].functions[0]
        assert func.intent == "validate email format"
        assert func.language is None

    def test_function_mapping_with_language_override(self, parser):
        spec = parser.parse(FULL_SPEC)
        func = spec.modules[2].functions[0]
        assert func.intent == "create user in database"
        assert func.language == "python"

    def test_module_description(self, parser):
        spec = parser.parse(FULL_SPEC)
        assert spec.modules[0].description == "Input validation predicates"

    def test_contracts_only_project(self, parser):
        spec = parser.parse(CONTRACTS_ONLY_SPEC)
        assert len(spec.data_contracts) == 1
        assert len(spec.modules) == 0

    def test_contract_fields(self, parser):
        spec = parser.parse(CONTRACTS_ONLY_SPEC)
        contract = spec.data_contracts[0]
        assert contract.name == "User"
        assert contract.fields == {"id": "string", "name": "string"}

    def test_all_supported_languages(self, parser):
        for lang in ("javascript", "typescript", "python", "go", "js", "ts", "py"):
            yaml_input = f"""
project:
  name: test
  language: {lang}
  modules:
    - name: mod
      functions:
        - do something
"""
            spec = parser.parse(yaml_input)
            assert spec.language == lang


class TestBuildOrder:
    def test_contracts_before_functions(self, parser):
        spec = parser.parse(FULL_SPEC)
        order = parser.build_order(spec)
        assert order[0] == "contract:User"
        assert order[1] == "contract:AuthToken"
        assert order[2] == "validation:validate email format"

    def test_order_preserves_module_sequence(self, parser):
        spec = parser.parse(FULL_SPEC)
        order = parser.build_order(spec)
        contract_items = [o for o in order if o.startswith("contract:")]
        function_items = [o for o in order if not o.startswith("contract:")]
        assert len(contract_items) == 2
        assert len(function_items) == 9

    def test_total_generation_count(self, parser):
        spec = parser.parse(FULL_SPEC)
        assert parser.total_generation_count(spec) == 11  # 2 contracts + 9 functions


class TestInvalidSpecs:
    def test_missing_project_key(self, parser):
        with pytest.raises(ProjectSpecError, match="Missing top-level 'project' key"):
            parser.parse("name: test")

    def test_project_not_mapping(self, parser):
        with pytest.raises(ProjectSpecError, match="'project' must be a mapping"):
            parser.parse("project: just a string")

    def test_missing_name(self, parser):
        with pytest.raises(ProjectSpecError, match="Missing required field 'name'"):
            parser.parse("""
project:
  language: typescript
  modules:
    - name: mod
      functions:
        - test
""")

    def test_missing_language(self, parser):
        with pytest.raises(ProjectSpecError, match="Missing required field 'language'"):
            parser.parse("""
project:
  name: test
  modules:
    - name: mod
      functions:
        - test
""")

    def test_unsupported_language(self, parser):
        with pytest.raises(ProjectSpecError, match="Unsupported language"):
            parser.parse("""
project:
  name: test
  language: rust
  modules:
    - name: mod
      functions:
        - test
""")

    def test_empty_project(self, parser):
        with pytest.raises(ProjectSpecError, match="at least one module"):
            parser.parse("""
project:
  name: test
  language: typescript
""")

    def test_empty_module_functions(self, parser):
        with pytest.raises(ProjectSpecError, match="non-empty 'functions' list"):
            parser.parse("""
project:
  name: test
  language: typescript
  modules:
    - name: mod
      functions: []
""")

    def test_duplicate_module_name(self, parser):
        with pytest.raises(ProjectSpecError, match="Duplicate module name"):
            parser.parse("""
project:
  name: test
  language: typescript
  modules:
    - name: auth
      functions:
        - login
    - name: auth
      functions:
        - logout
""")

    def test_duplicate_contract_name(self, parser):
        with pytest.raises(ProjectSpecError, match="Duplicate data contract name"):
            parser.parse("""
project:
  name: test
  language: typescript
  data_contracts:
    - name: User
      fields:
        id: string
    - name: User
      fields:
        name: string
  modules:
    - name: mod
      functions:
        - test
""")

    def test_contract_missing_fields(self, parser):
        with pytest.raises(ProjectSpecError, match="non-empty 'fields' mapping"):
            parser.parse("""
project:
  name: test
  language: typescript
  data_contracts:
    - name: User
  modules:
    - name: mod
      functions:
        - test
""")

    def test_invalid_yaml(self, parser):
        with pytest.raises(ProjectSpecError, match="Invalid YAML"):
            parser.parse("{ bad yaml: [")

    def test_non_mapping_yaml(self, parser):
        with pytest.raises(ProjectSpecError, match="must be a YAML mapping"):
            parser.parse("- just\n- a\n- list")

    def test_invalid_function_type(self, parser):
        with pytest.raises(ProjectSpecError, match="must be a string or mapping"):
            parser.parse("""
project:
  name: test
  language: typescript
  modules:
    - name: mod
      functions:
        - 42
""")

    def test_module_not_mapping(self, parser):
        with pytest.raises(ProjectSpecError, match="must be a mapping"):
            parser.parse("""
project:
  name: test
  language: typescript
  modules:
    - just a string
""")

    def test_contract_not_mapping(self, parser):
        with pytest.raises(ProjectSpecError, match="must be a mapping"):
            parser.parse("""
project:
  name: test
  language: typescript
  data_contracts:
    - just a string
  modules:
    - name: mod
      functions:
        - test
""")

    def test_empty_name(self, parser):
        with pytest.raises(ProjectSpecError, match="non-empty string"):
            parser.parse("""
project:
  name: ""
  language: typescript
  modules:
    - name: mod
      functions:
        - test
""")


class TestDataContracts:
    def test_frozen_spec(self, parser):
        spec = parser.parse(CONTRACTS_ONLY_SPEC)
        with pytest.raises(AttributeError):
            spec.name = "changed"  # type: ignore[misc]

    def test_contract_description(self, parser):
        spec = parser.parse(FULL_SPEC)
        assert spec.data_contracts[0].description == "Core user entity"
        assert spec.data_contracts[1].description == ""

    def test_contract_field_types(self, parser):
        spec = parser.parse(FULL_SPEC)
        user = spec.data_contracts[0]
        assert user.fields["id"] == "string"
        assert user.fields["email"] == "string"
        assert user.fields["createdAt"] == "Date"
