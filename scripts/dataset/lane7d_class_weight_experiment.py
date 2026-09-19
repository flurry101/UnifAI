"""
Lane 7D: LightGBM Class-Imbalance Experiment -- UnifAI SIH26099

Controlled experiment to determine whether Lane 7's minority-class failure
is primarily caused by multiclass class imbalance in training.

Does NOT modify:
  - Lane 5, Lane 6, production model, architecture, embeddings, or retrieval.

Runs 4 experiments with identical features/splits/seed, varying ONLY sample weights.

Outputs:
  outputs/lane7d_class_weight_experiment.json
  outputs/lane7d_class_weight_experiment.txt
  outputs/lane7d_predictions.csv
"""

import os, sys, json, math
import numpy as np
import pandas as pd
import lightgbm as lgb
from collections import Counter
from sklearn.metrics import (
    precision_recall_fscore_support, confusion_matrix,
    log_loss, balanced_accuracy_score
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ml.features import get_feature_names
from src.ml.dataset import CLASSES, map_label, build_grouped_dataset

# Paths
DIAGNOSTIC_CSV = "outputs/lane7c_feature_comparison.csv"
MODEL_DIR      = "outputs/lane7_model"
OUT_JSON       = "outputs/lane7d_class_weight_experiment.json"
OUT_TXT        = "outputs/lane7d_class_weight_experiment.txt"
OUT_CSV        = "outputs/lane7d_predictions.csv"

FEATURE_NAMES = get_feature_names()
NUM_CLASSES   = len(CLASSES)
RANDOM_STATE  = 42

# Base LightGBM params (identical to production, no weighting)
BASE_PARAMS = {
    "objective": "multiclass",
    "num_class": NUM_CLASSES,
    "metric": "multi_logloss",
    "boosting_type": "gbdt",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": 5,
    "verbose": -1,
    "random_state": RANDOM_STATE,
}


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


# ---------------------------------------------------------------
# WEIGHTING STRATEGIES
# ---------------------------------------------------------------
def compute_sample_weights(y_train, strategy):
    """
    Compute per-sample weights for multiclass LightGBM.

    LightGBM 4.7 multiclass uses the `weight` param on lgb.Dataset,
    NOT is_unbalance (binary-only) or scale_pos_weight (binary-only).
    """
    counts = Counter(y_train)
    n_samples = len(y_train)
    n_classes = len(counts)

    if strategy == "none":
        return np.ones(n_samples, dtype=np.float64)

    elif strategy == "inverse_frequency":
        # w_c = n_samples / (n_classes * count_c)
        class_weights = {}
        for cls_idx, cnt in counts.items():
            class_weights[cls_idx] = n_samples / (n_classes * cnt)
        weights = np.array([class_weights[y] for y in y_train], dtype=np.float64)
        return weights

    elif strategy == "sqrt_inverse":
        # Moderate: w_c = sqrt(n_samples / (n_classes * count_c))
        class_weights = {}
        for cls_idx, cnt in counts.items():
            class_weights[cls_idx] = np.sqrt(n_samples / (n_classes * cnt))
        weights = np.array([class_weights[y] for y in y_train], dtype=np.float64)
        return weights

    elif strategy == "capped_inverse":
        # Inverse frequency but capped at max_weight=50
        MAX_WEIGHT = 50.0
        class_weights = {}
        for cls_idx, cnt in counts.items():
            raw = n_samples / (n_classes * cnt)
            class_weights[cls_idx] = min(raw, MAX_WEIGHT)
        weights = np.array([class_weights[y] for y in y_train], dtype=np.float64)
        return weights

    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def report_class_weights(y_train, strategy):
    """Report the actual per-class weights used."""
    counts = Counter(y_train)
    n_samples = len(y_train)
    n_classes = len(counts)

    result = {}
    for cls_idx in sorted(counts.keys()):
        cls_name = CLASSES[cls_idx]
        cnt = counts[cls_idx]

        if strategy == "none":
            w = 1.0
        elif strategy == "inverse_frequency":
            w = n_samples / (n_classes * cnt)
        elif strategy == "sqrt_inverse":
            w = np.sqrt(n_samples / (n_classes * cnt))
        elif strategy == "capped_inverse":
            w = min(n_samples / (n_classes * cnt), 50.0)
        else:
            w = 1.0

        result[cls_name] = {
            "count": int(cnt),
            "weight": round(float(w), 4),
            "effective_count": round(float(cnt * w), 1),
        }
    return result


# ---------------------------------------------------------------
# TRAIN + EVALUATE
# ---------------------------------------------------------------
def train_and_evaluate(X_train, y_train, X_val, y_val, X_test, y_test,
                       feature_names, strategy, full_df=None):
    """Train LightGBM with given weighting and evaluate."""

    weights = compute_sample_weights(y_train.values, strategy)

    train_data = lgb.Dataset(
        X_train, label=y_train,
        feature_name=feature_names,
        weight=weights,
    )
    val_data = lgb.Dataset(
        X_val, label=y_val,
        feature_name=feature_names,
        reference=train_data,
    )

    callbacks = [lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(0)]
    model = lgb.train(
        BASE_PARAMS,
        train_data,
        num_boost_round=500,
        valid_sets=[train_data, val_data],
        callbacks=callbacks,
    )

    # Predictions on test set
    test_probs = model.predict(X_test)
    test_preds = np.argmax(test_probs, axis=1)
    y_test_arr = y_test.values

    # Per-class metrics
    p, r, f1, sup = precision_recall_fscore_support(
        y_test_arr, test_preds,
        labels=list(range(NUM_CLASSES)),
        zero_division=0
    )
    cm = confusion_matrix(y_test_arr, test_preds, labels=list(range(NUM_CLASSES)))

    # Macro / weighted
    p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(
        y_test_arr, test_preds, average="macro", zero_division=0
    )
    _, _, f1_wt, _ = precision_recall_fscore_support(
        y_test_arr, test_preds, average="weighted", zero_division=0
    )

    # Log loss
    try:
        ll = log_loss(y_test_arr, test_probs, labels=list(range(NUM_CLASSES)))
    except Exception:
        ll = None

    bal_acc = balanced_accuracy_score(y_test_arr, test_preds)

    per_class = {}
    for i, cls in enumerate(CLASSES):
        per_class[cls] = {
            "precision": round(float(p[i]), 4),
            "recall": round(float(r[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(sup[i]),
        }

    # Safety check: technical_conflict=True pairs predicted as IDENTICAL/EQUIVALENT
    safety = {"conflict_to_identical": 0, "conflict_to_equivalent": 0, "conflict_to_variant": 0}
    if full_df is not None:
        # Use test indices
        test_idx = X_test.index
        test_sub = full_df.loc[test_idx].copy()
        test_sub["predicted_idx"] = test_preds
        test_sub["predicted_class"] = [CLASSES[p] for p in test_preds]

        conflict_mask = test_sub["technical_conflict"] == 1.0
        true_distinct = test_sub["true_relation"] == "DISTINCT"

        safety["conflict_to_identical"] = int(
            ((conflict_mask) & (test_sub["predicted_class"] == "IDENTICAL")).sum()
        )
        safety["conflict_to_equivalent"] = int(
            ((conflict_mask) & (test_sub["predicted_class"] == "EQUIVALENT")).sum()
        )
        safety["conflict_to_variant"] = int(
            ((conflict_mask) & (test_sub["predicted_class"] == "VARIANT_OF")).sum()
        )
        # False positives: true DISTINCT predicted as positive
        safety["distinct_to_identical"] = int(
            ((true_distinct) & (test_sub["predicted_class"] == "IDENTICAL")).sum()
        )
        safety["distinct_to_equivalent"] = int(
            ((true_distinct) & (test_sub["predicted_class"] == "EQUIVALENT")).sum()
        )
        safety["distinct_to_variant"] = int(
            ((true_distinct) & (test_sub["predicted_class"] == "VARIANT_OF")).sum()
        )

    # Killer case: find the high-similarity identical pairs
    killer_cases = []
    if full_df is not None:
        test_sub = full_df.loc[X_test.index].copy()
        test_sub["pred_idx"] = test_preds
        for ci in range(NUM_CLASSES):
            test_sub[f"prob_{CLASSES[ci]}"] = test_probs[:, ci]

        killer = test_sub[
            (test_sub["true_relation"] == "IDENTICAL") &
            (test_sub["semantic_similarity"] > 0.99)
        ].head(3)
        for _, row in killer.iterrows():
            killer_cases.append({
                "query_id": row["query_id"],
                "candidate_id": row["candidate_id"],
                "semantic_similarity": round(float(row["semantic_similarity"]), 4),
                "true_relation": "IDENTICAL",
                "predicted": CLASSES[int(row["pred_idx"])],
                "P_IDENTICAL": round(float(row["prob_IDENTICAL"]), 6),
                "P_EQUIVALENT": round(float(row["prob_EQUIVALENT"]), 6),
                "P_VARIANT_OF": round(float(row["prob_VARIANT_OF"]), 6),
                "P_DISTINCT": round(float(row["prob_DISTINCT"]), 6),
            })

    # Feature importance
    try:
        imp = dict(zip(model.feature_name(), model.feature_importance(importance_type="gain")))
        imp_sorted = dict(sorted(imp.items(), key=lambda x: -x[1]))
    except Exception:
        imp_sorted = {}

    return {
        "strategy": strategy,
        "class_weights": report_class_weights(y_train.values, strategy),
        "per_class": per_class,
        "macro_f1": round(float(f1_mac), 4),
        "weighted_f1": round(float(f1_wt), 4),
        "log_loss": round(float(ll), 6) if ll is not None else None,
        "balanced_accuracy": round(float(bal_acc), 4),
        "confusion_matrix": cm.tolist(),
        "safety": safety,
        "killer_cases": killer_cases,
        "feature_importance_gain": imp_sorted,
        "num_iterations": model.num_trees() // NUM_CLASSES,
    }, model, test_probs, test_preds


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def run_experiment():
    print("Loading diagnostic dataset...")
    df = pd.read_csv(DIAGNOSTIC_CSV)
    print(f"Total pairs: {len(df)}")

    # Prepare features and labels
    features_list = [dict(row) for _, row in df[FEATURE_NAMES].iterrows()]
    labels = df["true_relation"].tolist()
    canonical_ids = df["canonical_id"].tolist()

    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        features_list, labels, canonical_ids,
        test_size=0.15, val_size=0.15, random_state=RANDOM_STATE
    )

    print(f"Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)}")

    # Map back to full df for safety analysis
    full_df = df.copy()
    full_df.index = range(len(full_df))
    # Rebuild with same indices as the split
    # Since build_grouped_dataset returns DataFrame slices, their index maps back
    train_indices = X_train.index.tolist()
    val_indices   = X_val.index.tolist()
    test_indices  = X_test.index.tolist()

    strategies = [
        ("A_unweighted", "none"),
        ("B_inverse_frequency", "inverse_frequency"),
        ("C_sqrt_inverse", "sqrt_inverse"),
        ("D_capped_inverse", "capped_inverse"),
    ]

    results = {}
    best_model = None
    best_preds = None
    best_probs = None
    best_strategy = None
    best_macro_f1 = -1

    for exp_name, strategy in strategies:
        print(f"\n{'='*60}")
        print(f"Experiment {exp_name} (strategy={strategy})")
        print(f"{'='*60}")

        result, model, probs, preds = train_and_evaluate(
            X_train, y_train, X_val, y_val, X_test, y_test,
            FEATURE_NAMES, strategy, full_df
        )
        results[exp_name] = result

        print(f"  Macro F1:       {result['macro_f1']}")
        print(f"  Balanced Acc:   {result['balanced_accuracy']}")
        print(f"  Log Loss:       {result['log_loss']}")
        for cls in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT"]:
            pc = result["per_class"][cls]
            print(f"  {cls:15s}: P={pc['precision']:.4f}  R={pc['recall']:.4f}  F1={pc['f1']:.4f}  n={pc['support']}")
        print(f"  Safety:")
        for k, v in result["safety"].items():
            print(f"    {k}: {v}")

        if result["macro_f1"] > best_macro_f1:
            best_macro_f1 = result["macro_f1"]
            best_strategy = exp_name
            best_model = model
            best_preds = preds
            best_probs = probs

    # ============================================================
    # VARIANT_OF SPECIAL ANALYSIS
    # ============================================================
    variant_analysis = {}
    for exp_name, result in results.items():
        cm = np.array(result["confusion_matrix"])
        vof_idx = CLASSES.index("VARIANT_OF")
        dist_idx = CLASSES.index("DISTINCT")

        vof_support = result["per_class"]["VARIANT_OF"]["support"]
        vof_predicted_total = int(cm[:, vof_idx].sum())
        vof_recall = result["per_class"]["VARIANT_OF"]["recall"]

        # How many true VARIANT_OF went to each class
        vof_row = cm[vof_idx] if vof_idx < len(cm) else [0] * NUM_CLASSES
        vof_confusion = {CLASSES[i]: int(vof_row[i]) for i in range(NUM_CLASSES)}

        variant_analysis[exp_name] = {
            "support": vof_support,
            "total_predicted_variant": vof_predicted_total,
            "recall": vof_recall,
            "confusion": vof_confusion,
        }

    # ============================================================
    # COMPARISON TABLE
    # ============================================================
    comparison = []
    for exp_name in results:
        r = results[exp_name]
        row = {
            "experiment": exp_name,
            "IDENTICAL_F1": r["per_class"]["IDENTICAL"]["f1"],
            "EQUIVALENT_F1": r["per_class"]["EQUIVALENT"]["f1"],
            "VARIANT_OF_F1": r["per_class"]["VARIANT_OF"]["f1"],
            "DISTINCT_F1": r["per_class"]["DISTINCT"]["f1"],
            "Macro_F1": r["macro_f1"],
            "Log_Loss": r["log_loss"],
            "Balanced_Acc": r["balanced_accuracy"],
        }
        comparison.append(row)

    # ============================================================
    # RECOMMENDATION
    # ============================================================
    baseline = results["A_unweighted"]
    best_result = results[best_strategy]

    improvement = {
        "IDENTICAL_F1_delta": round(
            best_result["per_class"]["IDENTICAL"]["f1"] - baseline["per_class"]["IDENTICAL"]["f1"], 4
        ),
        "EQUIVALENT_F1_delta": round(
            best_result["per_class"]["EQUIVALENT"]["f1"] - baseline["per_class"]["EQUIVALENT"]["f1"], 4
        ),
        "VARIANT_OF_F1_delta": round(
            best_result["per_class"]["VARIANT_OF"]["f1"] - baseline["per_class"]["VARIANT_OF"]["f1"], 4
        ),
        "DISTINCT_F1_delta": round(
            best_result["per_class"]["DISTINCT"]["f1"] - baseline["per_class"]["DISTINCT"]["f1"], 4
        ),
        "Macro_F1_delta": round(best_result["macro_f1"] - baseline["macro_f1"], 4),
    }

    # Safety assessment
    best_safety = best_result["safety"]
    safety_ok = (
        best_safety.get("conflict_to_identical", 0) == 0 and
        best_safety.get("conflict_to_equivalent", 0) == 0
    )

    adopt = (
        improvement["Macro_F1_delta"] > 0.05 and
        improvement["IDENTICAL_F1_delta"] >= 0 and
        improvement["EQUIVALENT_F1_delta"] >= 0 and
        safety_ok
    )

    recommendation = {
        "best_strategy": best_strategy,
        "improvement": improvement,
        "safety_preserved": safety_ok,
        "recommend_adoption": adopt,
        "reasoning": (
            f"Best strategy: {best_strategy}. "
            f"Macro F1 improved by {improvement['Macro_F1_delta']:+.4f}. "
            f"IDENTICAL F1 delta: {improvement['IDENTICAL_F1_delta']:+.4f}. "
            f"EQUIVALENT F1 delta: {improvement['EQUIVALENT_F1_delta']:+.4f}. "
            f"VARIANT_OF F1 delta: {improvement['VARIANT_OF_F1_delta']:+.4f}. "
            f"DISTINCT F1 delta: {improvement['DISTINCT_F1_delta']:+.4f}. "
            f"Safety preserved: {safety_ok}. "
            f"{'RECOMMEND adoption.' if adopt else 'DO NOT adopt yet -- further investigation needed.'}"
        ),
    }

    # ============================================================
    # ASSEMBLE REPORT
    # ============================================================
    report = {
        "experiments": results,
        "comparison_table": comparison,
        "variant_of_analysis": variant_analysis,
        "recommendation": recommendation,
        "best_strategy": best_strategy,
    }

    os.makedirs("outputs", exist_ok=True)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=safe_json)

    # ============================================================
    # TXT REPORT
    # ============================================================
    lines = []
    lines.append("=" * 72)
    lines.append("LANE 7D: LIGHTGBM CLASS-IMBALANCE EXPERIMENT")
    lines.append("UnifAI SIH26099")
    lines.append("=" * 72)

    lines.append("\nCOMPARISON TABLE")
    lines.append("-" * 72)
    header = f"{'Experiment':25s} {'IDENT F1':>9s} {'EQUIV F1':>9s} {'VAR F1':>9s} {'DIST F1':>9s} {'Macro F1':>9s} {'LogLoss':>9s}"
    lines.append(header)
    for row in comparison:
        lines.append(
            f"{row['experiment']:25s} "
            f"{row['IDENTICAL_F1']:9.4f} "
            f"{row['EQUIVALENT_F1']:9.4f} "
            f"{row['VARIANT_OF_F1']:9.4f} "
            f"{row['DISTINCT_F1']:9.4f} "
            f"{row['Macro_F1']:9.4f} "
            f"{str(row['Log_Loss']):>9s}"
        )

    lines.append("\nPER-EXPERIMENT DETAILS")
    lines.append("-" * 72)
    for exp_name, result in results.items():
        lines.append(f"\n  {exp_name}:")
        lines.append(f"  Class weights:")
        for cls, info in result["class_weights"].items():
            lines.append(f"    {cls:15s}: count={info['count']:>6d}  weight={info['weight']:>8.4f}  effective={info['effective_count']:>8.1f}")
        lines.append(f"  Iterations: {result['num_iterations']}")
        lines.append(f"  Per-class:")
        for cls in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT"]:
            pc = result["per_class"][cls]
            lines.append(f"    {cls:15s}: P={pc['precision']:.4f}  R={pc['recall']:.4f}  F1={pc['f1']:.4f}  n={pc['support']}")
        lines.append(f"  Safety:")
        for k, v in result["safety"].items():
            lines.append(f"    {k}: {v}")
        if result["killer_cases"]:
            lines.append(f"  Killer case (sim>=0.99, true=IDENTICAL):")
            for kc in result["killer_cases"][:2]:
                lines.append(
                    f"    pred={kc['predicted']}  P(IDENT)={kc['P_IDENTICAL']:.4f}  "
                    f"P(EQUIV)={kc['P_EQUIVALENT']:.4f}  P(DIST)={kc['P_DISTINCT']:.4f}"
                )

    lines.append("\nVARIANT_OF ANALYSIS")
    lines.append("-" * 72)
    for exp_name, va in variant_analysis.items():
        lines.append(f"  {exp_name}:")
        lines.append(f"    Support: {va['support']}  Predicted total: {va['total_predicted_variant']}  Recall: {va['recall']:.4f}")
        lines.append(f"    Confusion: {va['confusion']}")

    lines.append("\n" + "=" * 72)
    lines.append("RECOMMENDATION")
    lines.append("=" * 72)
    lines.append(f"\n  {recommendation['reasoning']}")
    lines.append(f"\n  Best: {recommendation['best_strategy']}")
    lines.append(f"  Adopt: {recommendation['recommend_adoption']}")
    lines.append(f"  Safety: {recommendation['safety_preserved']}")

    lines.append("\n" + "=" * 72)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Save predictions CSV for best model
    if best_probs is not None:
        pred_df = full_df.loc[X_test.index].copy()
        pred_df["predicted_class"] = [CLASSES[p] for p in best_preds]
        for i, cls in enumerate(CLASSES):
            pred_df[f"prob_{cls}"] = best_probs[:, i]
        pred_df.to_csv(OUT_CSV, index=False)

    print("\n" + "\n".join(lines[-15:]))
    print(f"\nOutputs: {OUT_JSON}, {OUT_TXT}, {OUT_CSV}")


if __name__ == "__main__":
    run_experiment()
