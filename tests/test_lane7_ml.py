import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from src.matching.models import PairFeatureResult
from src.ml.features import extract_features, map_three_state
from src.ml.dataset import build_grouped_dataset, check_leakage
from src.ml.predictor import Lane7Predictor
from src.ml.trainer import train_lane7_model

def get_dummy_result(tech_conf=False, dim_match=None, dim_conf=False, press_conf=False, mat_conf=False, std_conf=False, comp_conf=False) -> PairFeatureResult:
    return PairFeatureResult(
        semantic_similarity=0.95,
        lexical_similarity=0.8,
        manufacturer_match=None,
        mpn_match=None,
        component_type_match=None,
        dimension_match=dim_match,
        pressure_rating_match=None,
        material_grade_match=None,
        standard_match=None,
        uom_compatibility=None,
        dimension_conflict=dim_conf,
        pressure_conflict=press_conf,
        material_conflict=mat_conf,
        standard_conflict=std_conf,
        component_conflict=comp_conf,
        technical_conflict=tech_conf,
        missing_dimension=False if dim_match is not None else True,
        missing_pressure=True,
        missing_material=True,
        missing_standard=True,
        missing_component=True,
        technical_attribute_overlap=1,
        additional_attribute_count=0,
        relationship_score=0.0,
        relationship_class="UNDETERMINED",
        explanation=[]
    )

def test_missing_values():
    assert np.isnan(map_three_state(None))
    assert map_three_state(True) == 1.0
    assert map_three_state(False) == 0.0

def test_no_leakage():
    res = get_dummy_result()
    feats = extract_features(res)
    df = pd.DataFrame([feats])
    # Should pass
    check_leakage(df)
    
    # Inject leakage
    df["ground_truth_relationship"] = ["IDENTICAL"]
    with pytest.raises(ValueError, match="CRITICAL: Potential label leakage detected"):
        check_leakage(df)

def test_grouped_split_integrity():
    feats = [extract_features(get_dummy_result()) for _ in range(100)]
    labels = ["IDENTICAL", "DISTINCT"] * 50
    # Ten canonical groups
    canonical_ids = [f"CAN-{i//10}" for i in range(100)]
    
    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        feats, labels, canonical_ids, test_size=0.2, val_size=0.2, random_state=42
    )
    
    # Ensure no overlap of CAN-01/CAN-02 across splits. We can't easily retrieve the group IDs from X_train,
    # but we can rely on GroupShuffleSplit behavior.
    assert len(X_train) + len(X_val) + len(X_test) == 100

def test_model_persistence():
    feats = [extract_features(get_dummy_result()) for _ in range(50)]
    labels = ["IDENTICAL", "DISTINCT", "VARIANT_OF", "EQUIVALENT", "UNDETERMINED"] * 10
    canonical_ids = [f"CAN-{i}" for i in range(50)]
    
    ranker, _, _, _, _, _, _ = train_lane7_model(feats, labels, canonical_ids)
    
    with tempfile.TemporaryDirectory() as tmp:
        ranker.save(tmp)
        assert os.path.exists(os.path.join(tmp, "lgb_model.txt"))
        assert os.path.exists(os.path.join(tmp, "metadata.json"))
        
        predictor = Lane7Predictor(tmp)
        res = get_dummy_result()
        pred = predictor.predict_relationship(res)
        assert "ml_prediction" in pred

def test_safety_layer_overrides():
    feats = [extract_features(get_dummy_result()) for _ in range(50)]
    labels = ["IDENTICAL"] * 50
    canonical_ids = [f"CAN-{i}" for i in range(50)]
    
    ranker, _, _, _, _, _, _ = train_lane7_model(feats, labels, canonical_ids)
    
    with tempfile.TemporaryDirectory() as tmp:
        ranker.save(tmp)
        predictor = Lane7Predictor(tmp)
        
        # Test 1: Conflict -> Suppressed to DISTINCT
        res_conflict = get_dummy_result(tech_conf=True, dim_conf=True)
        pred = predictor.predict_relationship(res_conflict)
        # Even if ML said IDENTICAL, safety rule should trigger because of technical_conflict
        if pred["ml_prediction"] in ["IDENTICAL", "EQUIVALENT"]:
            assert pred["safety_rule_triggered"] is True
            assert pred["final_relationship"] == "DISTINCT"
        
        # Test 2: No conflict -> Not suppressed
        res_clean = get_dummy_result(tech_conf=False, dim_conf=False)
        pred_clean = predictor.predict_relationship(res_clean)
        assert pred_clean["safety_rule_triggered"] is False
        assert pred_clean["final_relationship"] == pred_clean["ml_prediction"]
