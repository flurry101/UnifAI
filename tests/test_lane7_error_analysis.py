"""
Tests for Lane 7 Error & Safety Analysis reproducibility.

These tests verify:
  1.  The analysis script can load the saved model.
  2.  Feature extraction is deterministic.
  3.  Safety layer correctly overrides hard-conflict predictions.
  4.  The analysis report JSON schema is complete.
  5.  Before-vs-after safety mapping is consistent.
"""

import os, sys, json, math
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.matching.models import PairFeatureResult
from src.ml.features import extract_features, get_feature_names
from src.ml.model import Lane7Ranker
from src.ml.dataset import CLASSES, map_label
from src.ml.predictor import Lane7Predictor

MODEL_DIR = "outputs/lane7_model"
REPORT_JSON = "outputs/lane7_error_analysis.json"


# ──────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────
def _make_result(**overrides):
    """Build a PairFeatureResult with defaults, overriding where needed."""
    defaults = dict(
        semantic_similarity=0.85,
        lexical_similarity=0.40,
        manufacturer_match=None,
        mpn_match=None,
        component_type_match=True,
        dimension_match=True,
        pressure_rating_match=True,
        material_grade_match=True,
        standard_match=True,
        uom_compatibility=True,
        dimension_conflict=False,
        pressure_conflict=False,
        material_conflict=False,
        standard_conflict=False,
        component_conflict=False,
        technical_conflict=False,
        missing_dimension=False,
        missing_pressure=False,
        missing_material=False,
        missing_standard=False,
        missing_component=False,
        technical_attribute_overlap=5,
        additional_attribute_count=0,
        relationship_score=0.9,
        relationship_class="EQUIVALENT",
        explanation=["Test"],
    )
    defaults.update(overrides)
    return PairFeatureResult(**defaults)


# ──────────────────────────────────────────────────────────────────
# 1.  Model loading
# ──────────────────────────────────────────────────────────────────
@pytest.mark.skipif(
    not os.path.exists(os.path.join(MODEL_DIR, "lgb_model.txt")),
    reason="Trained model not found – run lane7_validation.py first",
)
class TestModelLoading:
    def test_model_loads_successfully(self):
        ranker = Lane7Ranker()
        ranker.load(MODEL_DIR)
        assert ranker.model is not None

    def test_predictor_loads_successfully(self):
        predictor = Lane7Predictor(MODEL_DIR)
        assert predictor.ranker.model is not None

    def test_feature_schema_matches(self):
        ranker = Lane7Ranker()
        ranker.load(MODEL_DIR)
        assert ranker.features_schema == get_feature_names()


# ──────────────────────────────────────────────────────────────────
# 2.  Feature extraction determinism
# ──────────────────────────────────────────────────────────────────
class TestFeatureExtraction:
    def test_extract_features_keys(self):
        result = _make_result()
        feats = extract_features(result)
        assert set(feats.keys()) == set(get_feature_names())

    def test_three_state_none_is_nan(self):
        result = _make_result(dimension_match=None)
        feats = extract_features(result)
        assert math.isnan(feats["dimension_match"])

    def test_three_state_true_is_one(self):
        result = _make_result(dimension_match=True)
        feats = extract_features(result)
        assert feats["dimension_match"] == 1.0

    def test_three_state_false_is_zero(self):
        result = _make_result(dimension_match=False)
        feats = extract_features(result)
        assert feats["dimension_match"] == 0.0

    def test_bool_conflict_mapping(self):
        result = _make_result(technical_conflict=True)
        feats = extract_features(result)
        assert feats["technical_conflict"] == 1.0

    def test_deterministic_twice(self):
        result = _make_result()
        a = extract_features(result)
        b = extract_features(result)
        for k in a:
            va, vb = a[k], b[k]
            if isinstance(va, float) and math.isnan(va):
                assert math.isnan(vb)
            else:
                assert va == vb, f"Feature {k} differs: {va} vs {vb}"


# ──────────────────────────────────────────────────────────────────
# 3.  Safety layer correctness
# ──────────────────────────────────────────────────────────────────
@pytest.mark.skipif(
    not os.path.exists(os.path.join(MODEL_DIR, "lgb_model.txt")),
    reason="Trained model not found",
)
class TestSafetyLayer:
    def test_conflict_overrides_identical(self):
        """If ML predicts IDENTICAL but there is a hard conflict, safety must override."""
        predictor = Lane7Predictor(MODEL_DIR)
        result = _make_result(
            technical_conflict=True,
            dimension_conflict=True,
            semantic_similarity=0.99,
        )
        pred = predictor.predict_relationship(result)
        if pred["ml_prediction"] in ("IDENTICAL", "EQUIVALENT"):
            assert pred["safety_rule_triggered"] is True
            assert pred["final_relationship"] == "DISTINCT"

    def test_no_conflict_no_override(self):
        """If there is no conflict, safety should not trigger."""
        predictor = Lane7Predictor(MODEL_DIR)
        result = _make_result(technical_conflict=False)
        pred = predictor.predict_relationship(result)
        assert pred["safety_rule_triggered"] is False
        assert pred["ml_prediction"] == pred["final_relationship"]

    def test_conflict_does_not_affect_distinct(self):
        """If ML already predicts DISTINCT, conflict should not change anything."""
        predictor = Lane7Predictor(MODEL_DIR)
        result = _make_result(
            technical_conflict=True,
            semantic_similarity=0.10,
            lexical_similarity=0.05,
        )
        pred = predictor.predict_relationship(result)
        if pred["ml_prediction"] == "DISTINCT":
            assert pred["safety_rule_triggered"] is False
            assert pred["final_relationship"] == "DISTINCT"


# ──────────────────────────────────────────────────────────────────
# 4.  Report JSON schema (if report exists)
# ──────────────────────────────────────────────────────────────────
@pytest.mark.skipif(
    not os.path.exists(REPORT_JSON),
    reason="Report not yet generated – run lane7_error_analysis.py first",
)
class TestReportSchema:
    @pytest.fixture(autouse=True)
    def load_report(self):
        with open(REPORT_JSON, "r", encoding="utf-8") as f:
            self.report = json.load(f)

    def test_all_sections_present(self):
        expected_sections = [
            "1_per_class_metrics",
            "1b_aggregate_metrics",
            "2_confusion_matrix",
            "3_false_positive_analysis",
            "4_technical_safety_analysis",
            "5_high_similarity_conflict_analysis",
            "6_missing_information_analysis",
            "7_variant_of_analysis",
            "8_equivalent_analysis",
            "9_identical_analysis",
            "10_before_vs_after_safety",
            "11_feature_importance",
            "12_dataset_limitations",
            "key_findings",
        ]
        for section in expected_sections:
            assert section in self.report, f"Missing section: {section}"

    def test_per_class_has_all_classes(self):
        for cls in CLASSES:
            assert cls in self.report["1_per_class_metrics"]
            m = self.report["1_per_class_metrics"][cls]
            assert "Precision" in m
            assert "Recall" in m
            assert "F1" in m
            assert "Support" in m

    def test_confusion_matrix_dimensions(self):
        cm = self.report["2_confusion_matrix"]["matrix"]
        assert len(cm) == len(CLASSES)
        for row in cm:
            assert len(row) == len(CLASSES)

    def test_safety_analysis_keys(self):
        sa = self.report["4_technical_safety_analysis"]
        assert "total_pairs_with_hard_technical_conflict" in sa
        assert "overridden_by_safety_layer" in sa
        assert "incorrectly_allowed_through_safety" in sa

    def test_key_findings_not_empty(self):
        assert len(self.report["key_findings"]) > 5


# ──────────────────────────────────────────────────────────────────
# 5.  Label mapping
# ──────────────────────────────────────────────────────────────────
class TestLabelMapping:
    def test_known_classes(self):
        for cls in CLASSES:
            assert map_label(cls) == CLASSES.index(cls)

    def test_unrelated_maps_to_distinct(self):
        assert map_label("UNRELATED") == CLASSES.index("DISTINCT")

    def test_none_maps_to_undetermined(self):
        assert map_label(None) == CLASSES.index("UNDETERMINED")

    def test_nan_maps_to_undetermined(self):
        assert map_label(float("nan")) == CLASSES.index("UNDETERMINED")

    def test_unknown_string_maps_to_undetermined(self):
        assert map_label("GARBAGE_LABEL") == CLASSES.index("UNDETERMINED")
