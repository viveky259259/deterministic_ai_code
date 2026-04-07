"""Gate — halts pipeline when classification confidence < HIGH."""

from __future__ import annotations

from src.core.contracts import AmbiguityBlock, Classification, Confidence


class AmbiguityGate:
    """Hard gate between CanonicalClassifier and TemplateBinder."""

    def evaluate(self, classification: Classification) -> Classification | AmbiguityBlock:
        """Pass HIGH confidence through; halt MEDIUM/LOW with AmbiguityBlock."""
        if classification.confidence == Confidence.HIGH:
            return classification
        return self._build_ambiguity_block(classification)

    def _build_ambiguity_block(self, classification: Classification) -> AmbiguityBlock:
        """Construct AmbiguityBlock with appropriate question."""
        verb = classification.normalized.canonical_verb
        raw = classification.normalized.raw_input

        if classification.confidence == Confidence.MEDIUM:
            unclear = (
                f"Multiple intent types match for verb '{verb}': "
                f"could be {classification.intent_type.value} or another type"
            )
            question = (
                f"Is '{raw}' intended as a {classification.intent_type.value}? (yes/no)"
            )
            assumed = (
                f"Assuming {classification.intent_type.value} based on highest priority match"
            )
        else:
            unclear = f"Unrecognised verb or no matching intent type for: '{raw}'"
            question = (
                "What type of function is this? "
                "(pure_function / predicate / transformer / aggregator / "
                "side_effect_op / class_method / async_operation)"
            )
            assumed = f"Assuming PURE_FUNCTION as default for '{raw}'"

        return AmbiguityBlock(
            unclear_dimension=unclear,
            clarifying_question=question,
            assumed_interpretation=assumed,
            classification=classification,
        )
