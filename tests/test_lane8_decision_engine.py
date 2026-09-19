"""
Tests for Lane 8 Decision Engine — UnifAI SIH26099

Verifies:
  1.  High-confidence IDENTICAL
  2.  High-confidence EQUIVALENT
  3.  High-confidence VARIANT_OF
  4.  DISTINCT decision
  5.  Hard pressure conflict blocks IDENTICAL
  6.  Hard dimension conflict blocks IDENTICAL
  7.  Hard material conflict blocks EQUIVALENT
  8.  Missing pressure is NOT a conflict
  9.  Missing material is NOT a conflict
  10. Low probability margin
  11. High model probability + technical conflict
  12. High VARIANT_OF probability + technical conflict
  13. DISTINCT false-positive candidate
  14. Human-review routing
  15. No automatic APPROVED status
  16. Safety invariant: high prob cannot bypass conflict
"""

import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.matching.models import PairFeatureResult
from src.matching.lane8_decision import Lane8DecisionEngine


def _make_feature_result(**kwargs) -> PairFeatureResult:
    """Build a PairFeatureResult with sensible defaults."""
    defaults = dict(
        semantic_similarity=0.5,
        lexical_similarity=50.0,
        manufacturer_match=None,
        mpn_match=None,
        component_type_match=None,
        dimension_match=None,
        pressure_rating_match=None,
        material_grade_match=None,
        standard_match=None,
        uom_compatibility=True,
        dimension_conflict=False,
        pressure_conflict=False,
        material_conflict=False,
        standard_conflict=False,
        component_conflict=False,
        technical_conflict=False,
        missing_dimension=True,
        missing_pressure=True,
        missing_material=True,
        missing_standard=True,
        missing_component=True,
        technical_attribute_overlap=0,
        additional_attribute_count=0,
        relationship_score=0.0,
        relationship_class="UNDETERMINED",
        explanation=[],
    )
    defaults.update(kwargs)
    return PairFeatureResult(**defaults)


def _make_probs(ident=0.01, equiv=0.01, var=0.01, dist=0.96, undet=0.01):
    return {
        "IDENTICAL": ident,
        "EQUIVALENT": equiv,
        "VARIANT_OF": var,
        "DISTINCT": dist,
        "UNDETERMINED": undet,
    }


engine = Lane8DecisionEngine()


# ---------------------------------------------------------------
# 1. High-confidence IDENTICAL
# ---------------------------------------------------------------
class TestHighConfidenceIdentical:
    def test_strong_identical(self):
        fr = _make_feature_result(
            semantic_similarity=0.999,
            lexical_similarity=105.0,
            dimension_match=True,
            pressure_rating_match=True,
            component_type_match=True,
            missing_dimension=False,
            missing_pressure=False,
            missing_component=False,
        )
        probs = _make_probs(ident=0.70, equiv=0.15, var=0.05, dist=0.08, undet=0.02)
        d = engine.decide(fr, probs)
        assert d.final_relation == "IDENTICAL"
        assert d.confidence_level == "HIGH"
        assert d.decision_status == "PROPOSED"
        assert d.safety_rule_triggered is False


# ---------------------------------------------------------------
# 2. High-confidence EQUIVALENT
# ---------------------------------------------------------------
class TestHighConfidenceEquivalent:
    def test_strong_equivalent(self):
        fr = _make_feature_result(
            semantic_similarity=0.97,
            lexical_similarity=80.0,
            dimension_match=True,
            pressure_rating_match=True,
            missing_dimension=False,
            missing_pressure=False,
        )
        probs = _make_probs(ident=0.05, equiv=0.70, var=0.05, dist=0.15, undet=0.05)
        d = engine.decide(fr, probs)
        assert d.final_relation == "EQUIVALENT"
        assert d.confidence_level == "HIGH"
        assert d.decision_status == "PROPOSED"


# ---------------------------------------------------------------
# 3. High-confidence VARIANT_OF
# ---------------------------------------------------------------
class TestHighConfidenceVariant:
    def test_strong_variant(self):
        fr = _make_feature_result(
            semantic_similarity=0.95,
            lexical_similarity=72.0,
            dimension_match=True,
            additional_attribute_count=1,
            missing_dimension=False,
        )
        probs = _make_probs(ident=0.02, equiv=0.10, var=0.70, dist=0.15, undet=0.03)
        d = engine.decide(fr, probs)
        assert d.final_relation == "VARIANT_OF"
        assert d.confidence_level == "HIGH"
        assert d.decision_status == "PROPOSED"


# ---------------------------------------------------------------
# 4. DISTINCT decision
# ---------------------------------------------------------------
class TestDistinct:
    def test_clear_distinct(self):
        fr = _make_feature_result(semantic_similarity=0.30, lexical_similarity=20.0)
        probs = _make_probs(ident=0.01, equiv=0.01, var=0.01, dist=0.96, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.final_relation == "DISTINCT"
        assert d.confidence_level == "HIGH"
        assert d.decision_status == "PROPOSED"


# ---------------------------------------------------------------
# 5. Hard pressure conflict blocks IDENTICAL
# ---------------------------------------------------------------
class TestPressureConflictBlocksIdentical:
    def test_pressure_conflict_identical(self):
        fr = _make_feature_result(
            semantic_similarity=0.98,
            pressure_conflict=True,
            technical_conflict=True,
        )
        probs = _make_probs(ident=0.91, equiv=0.04, var=0.02, dist=0.02, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.final_relation != "IDENTICAL"
        assert d.final_relation != "EQUIVALENT"
        assert d.safety_rule_triggered is True
        assert d.human_review_required is True
        assert d.decision_status == "REVIEW"


# ---------------------------------------------------------------
# 6. Hard dimension conflict blocks IDENTICAL
# ---------------------------------------------------------------
class TestDimensionConflictBlocksIdentical:
    def test_dimension_conflict_identical(self):
        fr = _make_feature_result(
            semantic_similarity=0.99,
            dimension_conflict=True,
            technical_conflict=True,
        )
        probs = _make_probs(ident=0.85, equiv=0.08, var=0.03, dist=0.03, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.final_relation != "IDENTICAL"
        assert d.safety_rule_triggered is True


# ---------------------------------------------------------------
# 7. Hard material conflict blocks EQUIVALENT
# ---------------------------------------------------------------
class TestMaterialConflictBlocksEquivalent:
    def test_material_conflict_equivalent(self):
        fr = _make_feature_result(
            semantic_similarity=0.96,
            material_conflict=True,
            technical_conflict=True,
        )
        probs = _make_probs(ident=0.03, equiv=0.85, var=0.05, dist=0.05, undet=0.02)
        d = engine.decide(fr, probs)
        assert d.final_relation != "EQUIVALENT"
        assert d.safety_rule_triggered is True


# ---------------------------------------------------------------
# 8. Missing pressure is NOT a conflict
# ---------------------------------------------------------------
class TestMissingPressureNotConflict:
    def test_missing_pressure_not_conflict(self):
        fr = _make_feature_result(
            semantic_similarity=0.97,
            pressure_rating_match=None,  # MISSING, not False
            missing_pressure=True,
            pressure_conflict=False,     # Missing != conflict
            dimension_match=True,
            missing_dimension=False,
        )
        probs = _make_probs(ident=0.60, equiv=0.20, var=0.05, dist=0.10, undet=0.05)
        d = engine.decide(fr, probs)
        # Missing pressure should NOT trigger safety
        assert d.safety_rule_triggered is False
        # Should still be able to produce a positive decision
        assert d.final_relation in ("IDENTICAL", "EQUIVALENT", "VARIANT_OF", "UNDETERMINED")


# ---------------------------------------------------------------
# 9. Missing material is NOT a conflict
# ---------------------------------------------------------------
class TestMissingMaterialNotConflict:
    def test_missing_material_not_conflict(self):
        fr = _make_feature_result(
            semantic_similarity=0.95,
            material_grade_match=None,
            missing_material=True,
            material_conflict=False,
            dimension_match=True,
            missing_dimension=False,
        )
        probs = _make_probs(ident=0.05, equiv=0.65, var=0.10, dist=0.15, undet=0.05)
        d = engine.decide(fr, probs)
        assert d.safety_rule_triggered is False


# ---------------------------------------------------------------
# 10. Low probability margin
# ---------------------------------------------------------------
class TestLowMargin:
    def test_low_margin_causes_review(self):
        fr = _make_feature_result(semantic_similarity=0.90)
        # Very tight margin
        probs = _make_probs(ident=0.30, equiv=0.28, var=0.20, dist=0.20, undet=0.02)
        d = engine.decide(fr, probs)
        # Low probability + low margin should not produce HIGH confidence
        assert d.confidence_level != "HIGH"


# ---------------------------------------------------------------
# 11. High model probability + technical conflict
# ---------------------------------------------------------------
class TestHighProbWithConflict:
    def test_high_prob_blocked_by_conflict(self):
        fr = _make_feature_result(
            semantic_similarity=0.99,
            pressure_conflict=True,
            technical_conflict=True,
        )
        probs = _make_probs(ident=0.95, equiv=0.02, var=0.01, dist=0.01, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.final_relation != "IDENTICAL"
        assert d.final_relation != "EQUIVALENT"
        assert d.safety_rule_triggered is True
        assert "TECHNICAL_CONFLICT" in d.review_reason


# ---------------------------------------------------------------
# 12. High VARIANT_OF probability + technical conflict
# ---------------------------------------------------------------
class TestHighVariantWithConflict:
    def test_variant_blocked_by_conflict(self):
        fr = _make_feature_result(
            semantic_similarity=0.95,
            pressure_conflict=True,
            technical_conflict=True,
        )
        probs = _make_probs(ident=0.02, equiv=0.05, var=0.82, dist=0.10, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.final_relation != "VARIANT_OF"
        assert d.safety_rule_triggered is True
        assert d.human_review_required is True


# ---------------------------------------------------------------
# 13. Model probabilities are preserved
# ---------------------------------------------------------------
class TestModelProbsPreserved:
    def test_probs_preserved(self):
        fr = _make_feature_result(technical_conflict=True)
        probs = _make_probs(ident=0.90, equiv=0.05, var=0.02, dist=0.02, undet=0.01)
        d = engine.decide(fr, probs)
        # Even though safety triggered, original probs are preserved
        assert d.model_probabilities["IDENTICAL"] == 0.90
        assert d.model_predicted_relation == "IDENTICAL"


# ---------------------------------------------------------------
# 14. Human-review routing
# ---------------------------------------------------------------
class TestHumanReview:
    def test_conflict_routes_to_review(self):
        fr = _make_feature_result(technical_conflict=True, dimension_conflict=True)
        probs = _make_probs(ident=0.80, equiv=0.10, var=0.05, dist=0.04, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.human_review_required is True
        assert d.decision_status == "REVIEW"
        assert len(d.blocking_reasons) > 0


# ---------------------------------------------------------------
# 15. No automatic APPROVED status
# ---------------------------------------------------------------
class TestNoAutoApproved:
    def test_never_approved(self):
        fr = _make_feature_result(
            semantic_similarity=0.999,
            dimension_match=True,
            pressure_rating_match=True,
            material_grade_match=True,
        )
        probs = _make_probs(ident=0.99, equiv=0.005, var=0.002, dist=0.002, undet=0.001)
        d = engine.decide(fr, probs)
        assert d.decision_status != "APPROVED"


# ---------------------------------------------------------------
# 16. Safety invariant: high prob cannot bypass conflict
# ---------------------------------------------------------------
class TestSafetyInvariant:
    def test_invariant_identical(self):
        """No matter how high P(IDENTICAL), a conflict blocks it."""
        for prob_val in [0.50, 0.70, 0.90, 0.99]:
            fr = _make_feature_result(technical_conflict=True, pressure_conflict=True)
            probs = _make_probs(ident=prob_val, equiv=0.005, var=0.002,
                                dist=1.0 - prob_val - 0.008, undet=0.001)
            d = engine.decide(fr, probs)
            assert d.final_relation != "IDENTICAL", \
                f"IDENTICAL accepted with prob={prob_val} despite conflict"
            assert d.final_relation != "EQUIVALENT"

    def test_invariant_equivalent(self):
        """No matter how high P(EQUIVALENT), a conflict blocks it."""
        for prob_val in [0.50, 0.70, 0.90, 0.99]:
            fr = _make_feature_result(technical_conflict=True, dimension_conflict=True)
            probs = _make_probs(equiv=prob_val, ident=0.005, var=0.002,
                                dist=1.0 - prob_val - 0.008, undet=0.001)
            d = engine.decide(fr, probs)
            assert d.final_relation != "EQUIVALENT", \
                f"EQUIVALENT accepted with prob={prob_val} despite conflict"
            assert d.final_relation != "IDENTICAL"

    def test_invariant_variant(self):
        """Conflict blocks VARIANT_OF too."""
        fr = _make_feature_result(technical_conflict=True, pressure_conflict=True)
        probs = _make_probs(var=0.95, ident=0.01, equiv=0.01, dist=0.02, undet=0.01)
        d = engine.decide(fr, probs)
        assert d.final_relation != "VARIANT_OF"


# ---------------------------------------------------------------
# Additional: Evidence and explanation populated
# ---------------------------------------------------------------
class TestEvidencePopulated:
    def test_evidence_list_non_empty(self):
        fr = _make_feature_result(semantic_similarity=0.95, dimension_match=True)
        probs = _make_probs(equiv=0.70, dist=0.20)
        d = engine.decide(fr, probs)
        assert len(d.evidence) > 0

    def test_explanation_non_empty(self):
        fr = _make_feature_result()
        probs = _make_probs()
        d = engine.decide(fr, probs)
        assert len(d.explanation) > 0

    def test_deterministic_output(self):
        """Same input produces same output."""
        fr = _make_feature_result(semantic_similarity=0.80, dimension_match=True)
        probs = _make_probs(equiv=0.50, dist=0.40)
        d1 = engine.decide(fr, probs)
        d2 = engine.decide(fr, probs)
        assert d1.final_relation == d2.final_relation
        assert d1.confidence_level == d2.confidence_level
        assert d1.decision_status == d2.decision_status


# ---------------------------------------------------------------
# Ground-truth leakage test
# ---------------------------------------------------------------
class TestNoLeakage:
    def test_no_gt_in_decision_engine(self):
        import inspect
        from src.matching.lane8_decision import Lane8DecisionEngine
        source = inspect.getsource(Lane8DecisionEngine)
        assert "ground_truth" not in source.lower()
        assert "relation_type" not in source.lower()
        assert "canonical_id" not in source.lower()
