"""
Lane 7 Controlled Optimization — UnifAI SIH26099
Runs experiments A-F to systematically optimize the Lane 7 LightGBM model.
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
import lightgbm as lgb
from collections import Counter
from sklearn.metrics import precision_recall_fscore_support, log_loss
from sklearn.calibration import CalibratedClassifierCV

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.matching.models import PairFeatureResult
from src.matching.lane8_decision import Lane8DecisionEngine
from src.ml.features import get_feature_names
from src.ml.dataset import CLASSES, build_grouped_dataset

DIAGNOSTIC_CSV = "outputs/lane7c_feature_comparison.csv"
RANDOM_STATE = 42

def _row_to_feature_result(row) -> PairFeatureResult:
    def three_state(val):
        if pd.isna(val): return None
        return val == 1.0

    return PairFeatureResult(
        semantic_similarity=float(row["semantic_similarity"]),
        lexical_similarity=float(row["lexical_similarity"]),
        manufacturer_match=three_state(row.get("manufacturer_match")),
        mpn_match=three_state(row.get("mpn_match")),
        component_type_match=three_state(row.get("component_type_match")),
        dimension_match=three_state(row.get("dimension_match")),
        pressure_rating_match=three_state(row.get("pressure_rating_match")),
        material_grade_match=three_state(row.get("material_grade_match")),
        standard_match=three_state(row.get("standard_match")),
        uom_compatibility=three_state(row.get("uom_compatibility")),
        dimension_conflict=bool(row.get("dimension_conflict", 0)),
        pressure_conflict=bool(row.get("pressure_conflict", 0)),
        material_conflict=bool(row.get("material_conflict", 0)),
        standard_conflict=bool(row.get("standard_conflict", 0)),
        component_conflict=bool(row.get("component_conflict", 0)),
        technical_conflict=bool(row.get("technical_conflict", 0)),
        missing_dimension=bool(row.get("missing_dimension", 0)),
        missing_pressure=bool(row.get("missing_pressure", 0)),
        missing_material=bool(row.get("missing_material", 0)),
        missing_standard=bool(row.get("missing_standard", 0)),
        missing_component=bool(row.get("missing_component", 0)),
        technical_attribute_overlap=int(row.get("technical_attribute_overlap", 0)),
        additional_attribute_count=int(row.get("additional_attribute_count", 0)),
        relationship_score=0.0,
        relationship_class="UNDETERMINED",
        explanation=[],
    )

def train_and_evaluate(name, X_train, y_train, X_val, y_val, X_test, y_test, df_test, features, params, weights, engine):
    train_data = lgb.Dataset(X_train[features], label=y_train, feature_name=features, weight=weights)
    val_data = lgb.Dataset(X_val[features], label=y_val, feature_name=features, reference=train_data)
    
    callbacks = [lgb.early_stopping(stopping_rounds=20, verbose=False)]
    model = lgb.train(params, train_data, num_boost_round=1000, valid_sets=[train_data, val_data], callbacks=callbacks)
    
    # Predict
    test_probs = model.predict(X_test[features])
    test_preds_idx = np.argmax(test_probs, axis=1)
    lane7_preds = [CLASSES[p] for p in test_preds_idx]
    
    # Compute Metrics
    ll = log_loss(y_test, test_probs, labels=list(range(5)))
    p, r, f1, sup = precision_recall_fscore_support(y_test, test_preds_idx, labels=list(range(5)), zero_division=0)
    _, _, macro_f1, _ = precision_recall_fscore_support(y_test, test_preds_idx, average="macro", zero_division=0)
    
    # Lane 8
    violations = 0
    fp_positive = 0
    review_count = 0
    auto_count = 0
    
    for i, (_, row) in enumerate(df_test.iterrows()):
        fr = _row_to_feature_result(row)
        probs = {cls: float(test_probs[i, c_idx]) for c_idx, cls in enumerate(CLASSES)}
        decision = engine.decide(fr, probs)
        
        true_rel = row["true_relation"]
        pred_rel = lane7_preds[i]
        
        # Safety violation check
        # We check if Lane 7 raw model violates safety (auto-accept by model regardless of Lane 8)
        # OR we can just check if Lane 8 violates safety (which it never should).
        # Actually, the user asked to "verify that Lane 8 does NOT auto-accept IDENTICAL/EQUIVALENT" 
        # when technical_conflict == True. 
        if row["technical_conflict"] == 1.0 and decision.final_relation in ("IDENTICAL", "EQUIVALENT", "VARIANT_OF"):
            if decision.decision_status != "REVIEW":
                violations += 1
            
        # FP Positive Relation (predicted positive, true is distinct)
        if true_rel == "DISTINCT" and pred_rel in ("IDENTICAL", "EQUIVALENT", "VARIANT_OF"):
            fp_positive += 1
            
        if decision.human_review_required:
            review_count += 1
        elif decision.decision_status == "PROPOSED" and decision.final_relation in ("IDENTICAL", "EQUIVALENT", "VARIANT_OF"):
            auto_count += 1
            
    return {
        "Experiment": name,
        "IDENTICAL F1": round(float(f1[CLASSES.index("IDENTICAL")]), 4),
        "EQUIVALENT F1": round(float(f1[CLASSES.index("EQUIVALENT")]), 4),
        "VARIANT_OF F1": round(float(f1[CLASSES.index("VARIANT_OF")]), 4),
        "DISTINCT F1": round(float(f1[CLASSES.index("DISTINCT")]), 4),
        "Macro F1": round(float(macro_f1), 4),
        "Log Loss": round(float(ll), 4),
        "FP Positive": fp_positive,
        "Conflict Violations": violations,
        "Review Rate": round(review_count / len(y_test), 4),
        "Auto-Proposal Rate": round(auto_count / len(y_test), 4)
    }

def main():
    print("Loading data...")
    df = pd.read_csv(DIAGNOSTIC_CSV)
    
    FEATURE_NAMES = get_feature_names()
    features_list = [dict(row) for _, row in df[FEATURE_NAMES].iterrows()]
    labels = df["true_relation"].tolist()
    canonical_ids = df["canonical_id"].tolist()
    
    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        features_list, labels, canonical_ids, test_size=0.15, val_size=0.15, random_state=RANDOM_STATE
    )
    
    df_test = df.loc[X_test.index].copy()
    engine = Lane8DecisionEngine()
    
    # Basic params
    base_params = {
        "objective": "multiclass",
        "num_class": 5,
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "verbose": -1,
        "random_state": RANDOM_STATE,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": 5,
    }
    
    # Weight generation
    counts = Counter(y_train.values)
    n_samples = len(y_train)
    n_classes = len(counts)
    
    w_inv = np.array([n_samples / (n_classes * counts[y]) for y in y_train.values], dtype=np.float64)
    w_sqrt = np.array([math.sqrt(n_samples / (n_classes * counts[y])) for y in y_train.values], dtype=np.float64)
    w_none = np.ones_like(y_train.values, dtype=np.float64)
    
    results = []
    
    print("Running EXPERIMENT A: Baseline (Inverse Frequency)")
    res_a = train_and_evaluate("A_Baseline", X_train, y_train, X_val, y_val, X_test, y_test, df_test, FEATURE_NAMES, base_params, w_inv, engine)
    results.append(res_a)
    
    print("Running EXPERIMENT B: Sqrt Inverse Frequency")
    res_b1 = train_and_evaluate("B_Sqrt_Inv_Freq", X_train, y_train, X_val, y_val, X_test, y_test, df_test, FEATURE_NAMES, base_params, w_sqrt, engine)
    results.append(res_b1)
    
    print("Running EXPERIMENT B: Unweighted (for reference)")
    res_b2 = train_and_evaluate("B_Unweighted", X_train, y_train, X_val, y_val, X_test, y_test, df_test, FEATURE_NAMES, base_params, w_none, engine)
    results.append(res_b2)
    
    print("Running EXPERIMENT C: Hyperparameters (Conservative: L1/L2 reg, shallow)")
    hp1_params = dict(base_params)
    hp1_params.update({"num_leaves": 15, "max_depth": 4, "learning_rate": 0.02, "min_child_samples": 50, "lambda_l1": 0.1, "lambda_l2": 0.1})
    res_c1 = train_and_evaluate("C_Conservative_HP", X_train, y_train, X_val, y_val, X_test, y_test, df_test, FEATURE_NAMES, hp1_params, w_inv, engine)
    results.append(res_c1)
    
    print("Running EXPERIMENT C: Hyperparameters (Aggressive: deep)")
    hp2_params = dict(base_params)
    hp2_params.update({"num_leaves": 63, "max_depth": 7, "learning_rate": 0.05, "min_child_samples": 10})
    res_c2 = train_and_evaluate("C_Aggressive_HP", X_train, y_train, X_val, y_val, X_test, y_test, df_test, FEATURE_NAMES, hp2_params, w_inv, engine)
    results.append(res_c2)
    
    print("Running EXPERIMENT D: Feature Ablation (No Missingness Features)")
    no_miss_features = [f for f in FEATURE_NAMES if not f.startswith("missing_")]
    res_d1 = train_and_evaluate("D_Ablation_NoMiss", X_train, y_train, X_val, y_val, X_test, y_test, df_test, no_miss_features, base_params, w_inv, engine)
    results.append(res_d1)
    
    print("Running EXPERIMENT D: Feature Ablation (Retrieval Only)")
    retrieval_features = ["semantic_similarity", "lexical_similarity"]
    res_d2 = train_and_evaluate("D_Ablation_RetrievalOnly", X_train, y_train, X_val, y_val, X_test, y_test, df_test, retrieval_features, base_params, w_inv, engine)
    results.append(res_d2)

    # Save Results
    out_df = pd.DataFrame(results)
    print("\n" + "="*90)
    print(out_df.to_string(index=False))
    print("="*90)
    
    os.makedirs("outputs", exist_ok=True)
    out_df.to_csv("outputs/lane7_improvement_experiments.csv", index=False)
    print("Saved to outputs/lane7_improvement_experiments.csv")

if __name__ == "__main__":
    main()
