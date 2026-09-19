"""
Lane 8 Validation — UnifAI SIH26099

Runs Lane 8 Decision Engine on the Lane 7D weighted LightGBM predictions.
Compares raw Lane 7 vs Lane 8 final decisions.

Outputs:
  outputs/lane8_validation.json
  outputs/lane8_validation.txt
"""

import os, sys, json, math
import numpy as np
import pandas as pd
import lightgbm as lgb
from collections import Counter
from sklearn.metrics import (
    precision_recall_fscore_support, confusion_matrix,
    balanced_accuracy_score
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.matching.models import PairFeatureResult
from src.matching.lane8_decision import Lane8DecisionEngine
from src.matching.lane8_models import Lane8Decision
from src.ml.features import get_feature_names
from src.ml.dataset import CLASSES, build_grouped_dataset

DIAGNOSTIC_CSV = "outputs/lane7c_feature_comparison.csv"
OUT_JSON       = "outputs/lane8_validation.json"
OUT_TXT        = "outputs/lane8_validation.txt"
FEATURE_NAMES  = get_feature_names()
RANDOM_STATE   = 42


def safe_json(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if math.isnan(obj) else float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


def _row_to_feature_result(row) -> PairFeatureResult:
    """Reconstruct PairFeatureResult from a CSV row."""
    def three_state(val):
        if pd.isna(val):
            return None
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


def compute_metrics(y_true_str, y_pred_str, label=""):
    """Compute per-class and macro metrics from string labels."""
    all_labels = ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT", "UNDETERMINED"]
    label_to_idx = {l: i for i, l in enumerate(all_labels)}

    y_true = [label_to_idx.get(y, 4) for y in y_true_str]
    y_pred = [label_to_idx.get(y, 4) for y in y_pred_str]

    p, r, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(len(all_labels))), zero_division=0
    )
    p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(all_labels))))

    per_class = {}
    for i, cls in enumerate(all_labels):
        per_class[cls] = {
            "precision": round(float(p[i]), 4),
            "recall": round(float(r[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(sup[i]),
        }

    return {
        "per_class": per_class,
        "macro_f1": round(float(f1_mac), 4),
        "confusion_matrix": cm.tolist(),
    }


def run_validation():
    print("Loading diagnostic dataset...")
    df = pd.read_csv(DIAGNOSTIC_CSV)
    print(f"Total pairs: {len(df)}")

    # Rebuild splits (same as Lane 7D)
    features_list = [dict(row) for _, row in df[FEATURE_NAMES].iterrows()]
    labels = df["true_relation"].tolist()
    canonical_ids = df["canonical_id"].tolist()

    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        features_list, labels, canonical_ids,
        test_size=0.15, val_size=0.15, random_state=RANDOM_STATE
    )

    # Retrain weighted model (inverse-frequency, same as Lane 7D best)
    print("Training weighted LightGBM (Lane 7D best: inverse-frequency)...")
    counts = Counter(y_train.values)
    n_samples = len(y_train)
    n_classes = len(counts)
    class_weights = {cls: n_samples / (n_classes * cnt) for cls, cnt in counts.items()}
    weights = np.array([class_weights[y] for y in y_train.values], dtype=np.float64)

    params = {
        "objective": "multiclass",
        "num_class": 5,
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": 5,
        "verbose": -1,
        "random_state": RANDOM_STATE,
    }

    train_data = lgb.Dataset(X_train, label=y_train, feature_name=FEATURE_NAMES, weight=weights)
    val_data = lgb.Dataset(X_val, label=y_val, feature_name=FEATURE_NAMES, reference=train_data)

    callbacks = [lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(0)]
    model = lgb.train(params, train_data, num_boost_round=500,
                      valid_sets=[train_data, val_data], callbacks=callbacks)

    # Predict on test set
    test_probs = model.predict(X_test)
    test_preds_idx = np.argmax(test_probs, axis=1)
    lane7_predictions = [CLASSES[p] for p in test_preds_idx]

    test_df = df.loc[X_test.index].copy()
    test_df["lane7_prediction"] = lane7_predictions
    for i, cls in enumerate(CLASSES):
        test_df[f"prob_{cls}"] = test_probs[:, i]

    true_labels = test_df["true_relation"].tolist()

    # ============================================================
    # RUN LANE 8
    # ============================================================
    print("Running Lane 8 Decision Engine on test set...")
    engine = Lane8DecisionEngine()
    lane8_decisions = []
    lane8_relations = []

    for idx, row in test_df.iterrows():
        fr = _row_to_feature_result(row)
        probs = {cls: float(row[f"prob_{cls}"]) for cls in CLASSES}
        decision = engine.decide(fr, probs)
        lane8_decisions.append(decision)
        lane8_relations.append(decision.final_relation)

    test_df["lane8_relation"] = lane8_relations
    test_df["lane8_confidence"] = [d.confidence_level for d in lane8_decisions]
    test_df["lane8_status"] = [d.decision_status for d in lane8_decisions]
    test_df["lane8_safety_triggered"] = [d.safety_rule_triggered for d in lane8_decisions]
    test_df["lane8_review_required"] = [d.human_review_required for d in lane8_decisions]

    # ============================================================
    # METRICS
    # ============================================================
    print("Computing metrics...")

    lane7_metrics = compute_metrics(true_labels, lane7_predictions, "Lane7")
    lane8_metrics = compute_metrics(true_labels, lane8_relations, "Lane8")

    # Baseline: always DISTINCT
    baseline_preds = ["DISTINCT"] * len(true_labels)
    baseline_metrics = compute_metrics(true_labels, baseline_preds, "Baseline")

    # ============================================================
    # SAFETY ANALYSIS
    # ============================================================
    conflict_mask = test_df["technical_conflict"] == 1.0
    true_distinct = test_df["true_relation"] == "DISTINCT"

    lane7_safety = {
        "conflict_to_identical": int((conflict_mask & (test_df["lane7_prediction"] == "IDENTICAL")).sum()),
        "conflict_to_equivalent": int((conflict_mask & (test_df["lane7_prediction"] == "EQUIVALENT")).sum()),
        "conflict_to_variant": int((conflict_mask & (test_df["lane7_prediction"] == "VARIANT_OF")).sum()),
        "distinct_to_identical": int((true_distinct & (test_df["lane7_prediction"] == "IDENTICAL")).sum()),
        "distinct_to_equivalent": int((true_distinct & (test_df["lane7_prediction"] == "EQUIVALENT")).sum()),
        "distinct_to_variant": int((true_distinct & (test_df["lane7_prediction"] == "VARIANT_OF")).sum()),
    }
    lane8_safety = {
        "conflict_to_identical": int((conflict_mask & (test_df["lane8_relation"] == "IDENTICAL")).sum()),
        "conflict_to_equivalent": int((conflict_mask & (test_df["lane8_relation"] == "EQUIVALENT")).sum()),
        "conflict_to_variant": int((conflict_mask & (test_df["lane8_relation"] == "VARIANT_OF")).sum()),
        "distinct_to_identical": int((true_distinct & (test_df["lane8_relation"] == "IDENTICAL")).sum()),
        "distinct_to_equivalent": int((true_distinct & (test_df["lane8_relation"] == "EQUIVALENT")).sum()),
        "distinct_to_variant": int((true_distinct & (test_df["lane8_relation"] == "VARIANT_OF")).sum()),
    }

    # ============================================================
    # CONFIDENCE & REVIEW DISTRIBUTION
    # ============================================================
    confidence_dist = dict(Counter(d.confidence_level for d in lane8_decisions))
    status_dist = dict(Counter(d.decision_status for d in lane8_decisions))
    review_count = sum(1 for d in lane8_decisions if d.human_review_required)
    safety_triggered_count = sum(1 for d in lane8_decisions if d.safety_rule_triggered)
    undetermined_count = sum(1 for d in lane8_decisions if d.final_relation == "UNDETERMINED")

    auto_accept_count = sum(1 for d in lane8_decisions
                            if d.decision_status == "PROPOSED"
                            and d.final_relation in ("IDENTICAL", "EQUIVALENT", "VARIANT_OF"))

    # ============================================================
    # EXAMPLE DECISIONS
    # ============================================================
    examples = []
    for i, d in enumerate(lane8_decisions[:500]):
        if d.safety_rule_triggered or d.final_relation != d.model_predicted_relation:
            row = test_df.iloc[i]
            examples.append({
                "query_id": row.get("query_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "true_relation": row["true_relation"],
                "model_predicted": d.model_predicted_relation,
                "lane8_final": d.final_relation,
                "confidence": d.confidence_level,
                "safety_triggered": d.safety_rule_triggered,
                "review_reason": d.review_reason,
                "explanation": d.explanation[:120],
            })
            if len(examples) >= 10:
                break

    # ============================================================
    # REPORT
    # ============================================================
    report = {
        "baseline_metrics": baseline_metrics,
        "lane7_metrics": lane7_metrics,
        "lane8_metrics": lane8_metrics,
        "lane7_safety": lane7_safety,
        "lane8_safety": lane8_safety,
        "confidence_distribution": confidence_dist,
        "status_distribution": status_dist,
        "review_count": review_count,
        "safety_triggered_count": safety_triggered_count,
        "undetermined_count": undetermined_count,
        "auto_accept_positive": auto_accept_count,
        "total_test": len(test_df),
        "example_decisions": examples,
    }

    os.makedirs("outputs", exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=safe_json)

    # ============================================================
    # TXT REPORT
    # ============================================================
    lines = []
    lines.append("=" * 72)
    lines.append("LANE 8 VALIDATION REPORT")
    lines.append("UnifAI SIH26099")
    lines.append("=" * 72)

    lines.append("\nCOMPARISON: Baseline vs Lane 7 (weighted) vs Lane 8")
    lines.append("-" * 72)
    header = f"{'Model':20s} {'IDENT F1':>9s} {'EQUIV F1':>9s} {'VAR F1':>9s} {'DIST F1':>9s} {'UNDET F1':>9s} {'Macro F1':>9s}"
    lines.append(header)
    for name, m in [("Baseline(DISTINCT)", baseline_metrics),
                    ("Lane7 Weighted", lane7_metrics),
                    ("Lane8 Decision", lane8_metrics)]:
        pc = m["per_class"]
        lines.append(
            f"{name:20s} "
            f"{pc['IDENTICAL']['f1']:9.4f} "
            f"{pc['EQUIVALENT']['f1']:9.4f} "
            f"{pc['VARIANT_OF']['f1']:9.4f} "
            f"{pc['DISTINCT']['f1']:9.4f} "
            f"{pc.get('UNDETERMINED', {}).get('f1', 0):9.4f} "
            f"{m['macro_f1']:9.4f}"
        )

    lines.append("\nPER-CLASS DETAIL")
    lines.append("-" * 72)
    for name, m in [("Lane7", lane7_metrics), ("Lane8", lane8_metrics)]:
        lines.append(f"\n  {name}:")
        for cls in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT", "UNDETERMINED"]:
            pc = m["per_class"].get(cls, {})
            if pc.get("support", 0) > 0 or pc.get("f1", 0) > 0:
                lines.append(f"    {cls:15s}: P={pc['precision']:.4f}  R={pc['recall']:.4f}  F1={pc['f1']:.4f}  n={pc['support']}")

    lines.append("\nSAFETY COMPARISON")
    lines.append("-" * 72)
    lines.append(f"  {'Metric':40s} {'Lane7':>8s} {'Lane8':>8s}")
    for key in lane7_safety:
        lines.append(f"  {key:40s} {lane7_safety[key]:8d} {lane8_safety[key]:8d}")

    lines.append("\nCONFIDENCE DISTRIBUTION")
    lines.append("-" * 72)
    for level, count in sorted(confidence_dist.items()):
        lines.append(f"  {level:10s}: {count}")

    lines.append(f"\nDECISION STATUS")
    for st, count in sorted(status_dist.items()):
        lines.append(f"  {st:10s}: {count}")

    lines.append(f"\n  Auto-accept (positive): {auto_accept_count}")
    lines.append(f"  Human review required:  {review_count}")
    lines.append(f"  Safety triggered:       {safety_triggered_count}")
    lines.append(f"  UNDETERMINED:           {undetermined_count}")

    lines.append("\nEXAMPLE DECISIONS (safety-triggered or model-overridden)")
    lines.append("-" * 72)
    for ex in examples[:5]:
        lines.append(
            f"  true={ex['true_relation']:12s} model={ex['model_predicted']:12s} "
            f"lane8={ex['lane8_final']:12s} conf={ex['confidence']:8s} "
            f"safety={ex['safety_triggered']}"
        )
        lines.append(f"    {ex['explanation']}")

    lines.append("\n" + "=" * 72)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines))
    print(f"\nOutputs: {OUT_JSON}, {OUT_TXT}")


if __name__ == "__main__":
    run_validation()
