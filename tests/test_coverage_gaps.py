"""Tests to cover remaining gaps in coverage."""

import pytest

from src.core.canonical_classifier import CanonicalClassifier
from src.core.contracts import (
    CanonicalType,
    Classification,
    Confidence,
    NormalizedIntent,
    ParsedSections,
)
from src.core.schema_parser import SchemaParser
from src.core.template_binder import TemplateBinder


def _ni(verb: str, raw: str) -> NormalizedIntent:
    return NormalizedIntent(verb, "Test", raw, "freetext")


class TestClassifierMediumConfidence:
    """Cover lines 44-46: two rules match → MEDIUM."""

    def test_validate_with_is_keyword_medium(self):
        """'validate' verb + 'is' keyword → PREDICATE matches twice? Actually both
        just match PREDICATE. Let's find a genuine multi-match."""
        c = CanonicalClassifier()
        # 'fetch' matches ASYNC_OPERATION, 'is' keyword matches PREDICATE → MEDIUM
        ni = _ni("fetch", "is the data fetch complete")
        result = c.classify(ni, "javascript")
        assert result.confidence == Confidence.MEDIUM

    def test_save_with_method_keyword(self):
        """'save' verb → SIDE_EFFECT_OP, 'method' keyword → CLASS_METHOD → MEDIUM."""
        c = CanonicalClassifier()
        ni = _ni("save", "save method on class user")
        result = c.classify(ni, "javascript")
        assert result.confidence == Confidence.MEDIUM


class TestClassifierAggregator:
    """Cover line 83: AGGREGATOR with collection noun + keyword."""

    def test_count_users_aggregator(self):
        c = CanonicalClassifier()
        ni = _ni("calculate", "count active users")
        result = c.classify(ni, "javascript")
        # 'calculate' → PURE_FUNCTION, 'users' + 'count' → AGGREGATOR → MEDIUM
        assert CanonicalType.AGGREGATOR in [
            m for m in c._evaluate_rules(ni)
        ]

    def test_filter_items_aggregator(self):
        c = CanonicalClassifier()
        ni = _ni("unknown", "filter items by status")
        matches = c._evaluate_rules(ni)
        assert CanonicalType.AGGREGATOR in matches


class TestClassifierClassMethod:
    """Cover line 91: CLASS_METHOD keyword match."""

    def test_method_keyword(self):
        c = CanonicalClassifier()
        ni = _ni("unknown", "add a method inside the user class")
        matches = c._evaluate_rules(ni)
        assert CanonicalType.CLASS_METHOD in matches

    def test_member_of_keyword(self):
        c = CanonicalClassifier()
        ni = _ni("unknown", "member of the account class")
        matches = c._evaluate_rules(ni)
        assert CanonicalType.CLASS_METHOD in matches


class TestSchemaParserMultipleCodeBlocks:
    """Cover lines 86-87: multiple fenced code blocks in IMPLEMENTATION."""

    def test_multiple_code_blocks_returns_none(self):
        parser = SchemaParser()
        raw = """
---INTENT_CLASSIFICATION---
type: PURE_FUNCTION

---SIGNATURE---
js: const total = ...

---IMPLEMENTATION---
```javascript
const total = (a, b) => a + b;
```
```javascript
const other = (a, b) => a - b;
```

---INVARIANTS---
preconditions: ...

---TEST_ORACLE---
```javascript
assert(true);
```
---
"""
        result = parser.parse(raw)
        assert result is None


class TestSchemaParserEmptyCode:
    """Cover line 91: empty code after fence stripping."""

    def test_empty_code_after_strip(self):
        parser = SchemaParser()
        raw = """
---INTENT_CLASSIFICATION---
type: PURE_FUNCTION

---SIGNATURE---
js: ...

---IMPLEMENTATION---
```javascript
```

---INVARIANTS---
...

---TEST_ORACLE---
```javascript
assert(true);
```
---
"""
        result = parser.parse(raw)
        assert result is None


class TestTemplateBinder:
    """Cover line 154: reduce_prefix naming rule."""

    def test_aggregator_reduce_prefix(self):
        binder = TemplateBinder()
        ni = NormalizedIntent("add", "Orders", "sum all orders", "freetext")
        c = Classification(CanonicalType.AGGREGATOR, Confidence.HIGH, ni, "javascript")
        bp = binder.bind(c)
        assert "Function name: reduceOrders" in bp.user_message

    def test_aggregator_python_snake_case(self):
        binder = TemplateBinder()
        ni = NormalizedIntent("add", "Orders", "sum all orders", "freetext")
        c = Classification(CanonicalType.AGGREGATOR, Confidence.HIGH, ni, "python")
        bp = binder.bind(c)
        assert "Function name: reduce_orders" in bp.user_message
