"""Tests for SpecValidator."""

import pytest

from src.core.contracts import CanonicalType, Confidence
from src.core.spec_validator import SchemaError, SpecValidator


@pytest.fixture
def validator():
    return SpecValidator()


VALID_YAML = """
intent: pure_function
verb: add
noun: Total
params:
  - name: firstNumber
    type: number
  - name: secondNumber
    type: number
returns: number
language: javascript
"""

VALID_JSON = '{"intent": "predicate", "verb": "validate", "noun": "EvenNumber", "language": "javascript"}'


class TestValidSpecs:
    def test_yaml_spec(self, validator):
        c = validator.validate(VALID_YAML)
        assert c.intent_type == CanonicalType.PURE_FUNCTION
        assert c.confidence == Confidence.HIGH
        assert c.normalized.canonical_verb == "add"
        assert c.normalized.canonical_noun == "Total"
        assert c.language == "javascript"

    def test_json_spec(self, validator):
        c = validator.validate(VALID_JSON)
        assert c.intent_type == CanonicalType.PREDICATE
        assert c.confidence == Confidence.HIGH
        assert c.normalized.canonical_verb == "validate"

    def test_confidence_always_high(self, validator):
        c = validator.validate(VALID_YAML)
        assert c.confidence == Confidence.HIGH

    def test_no_synonym_lookup(self, validator):
        """Spec with verb 'sum' should NOT be normalized to 'add'."""
        yaml_input = """
intent: pure_function
verb: sum
noun: Total
language: javascript
"""
        c = validator.validate(yaml_input)
        assert c.normalized.canonical_verb == "sum"  # NOT 'add'

    def test_yaml_source_tag(self, validator):
        c = validator.validate(VALID_YAML)
        assert c.normalized.source == "yaml_spec"

    def test_json_source_tag(self, validator):
        c = validator.validate(VALID_JSON)
        assert c.normalized.source == "json_spec"

    def test_data_contract_spec(self, validator):
        spec = """
intent: data_contract
verb: define
noun: User
language: typescript
"""
        c = validator.validate(spec)
        assert c.intent_type == CanonicalType.DATA_CONTRACT
        assert c.confidence == Confidence.HIGH


class TestInvalidSpecs:
    def test_missing_verb_raises(self, validator):
        bad = """
intent: pure_function
noun: Total
language: javascript
"""
        with pytest.raises(SchemaError, match="Missing required field: verb"):
            validator.validate(bad)

    def test_missing_intent_raises(self, validator):
        bad = """
verb: add
noun: Total
language: javascript
"""
        with pytest.raises(SchemaError, match="Missing required field: intent"):
            validator.validate(bad)

    def test_unknown_intent_type(self, validator):
        bad = """
intent: unknown_type
verb: add
noun: Total
language: javascript
"""
        with pytest.raises(SchemaError, match="Unknown intent type: unknown_type"):
            validator.validate(bad)

    def test_unsupported_language(self, validator):
        bad = """
intent: pure_function
verb: add
noun: Total
language: rust
"""
        with pytest.raises(SchemaError, match="Unsupported language: rust"):
            validator.validate(bad)

    def test_invalid_yaml_syntax(self, validator):
        with pytest.raises(SchemaError, match="Invalid spec format"):
            validator.validate("{ bad yaml: [")

    def test_non_mapping_yaml(self, validator):
        with pytest.raises(SchemaError, match="Invalid spec format"):
            validator.validate("- just\n- a\n- list")
