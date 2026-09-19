"""
Lane 7C: LightGBM Minority-Class Failure Diagnosis -- UnifAI SIH26099

READ-ONLY diagnostic.  Does NOT modify any production code, model, or data.

Determines WHY LightGBM predicts DISTINCT for true IDENTICAL/EQUIVALENT/VARIANT_OF
pairs even though Lane 5 retrieves them at 100% Recall@100.

Distinguishes between:
  A. Feature insufficiency
  B. Training / class imbalance
  C. Model configuration
  D. Probability / decision threshold
  E. Benchmark / label issue

Outputs:
  outputs/lane7c_model_diagnosis.json
  outputs/lane7c_model_diagnosis.txt
  outputs/lane7c_feature_comparison.csv
"""

import os, sys, json, math, statistics
import numpy as np
import pandas as pd
from tqdm import tqdm
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.retrieval.engine import RetrievalEngine
from src.retrieval.vector_store import PostgresVectorStore
from src.retrieval.embeddings import Qwen3EmbeddingProvider
from src.retrieval.lexical import BM25Retriever
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline
from src.extraction.engine import ExtractionEngine
from src.matching.lane6_features import PairFeatureEngine
from src.matching.models import Pair, PairFeatureResult
from src.ml.features import extract_features, get_feature_names
from src.ml.model import Lane7Ranker
from src.ml.dataset import CLASSES, map_label, build_grouped_dataset
from dotenv import load_dotenv

load_dotenv()

SYNTHETIC_MASTER = "data/synthetic/material_master.csv"
SYNTHETIC_GT     = "data/synthetic/ground_truth_relationships.csv"
CORPUS_PATH      = "data/real_public/real_cpse_materials.csv"
MODEL_DIR        = "outputs/lane7_model"
OUT_JSON         = "outputs/lane7c_model_diagnosis.json"
OUT_TXT          = "outputs/lane7c_model_diagnosis.txt"
OUT_CSV          = "outputs/lane7c_feature_comparison.csv"

FEATURE_NAMES = get_feature_names()

THREE_STATE_FEATURES = [
    "manufacturer_match", "mpn_match", "component_type_match",
    "dimension_match", "pressure_rating_match", "material_grade_match",
    "standard_match", "uom_compatibility"
]
BOOL_FEATURES = [
    "dimension_conflict", "pressure_conflict", "material_conflict",
    "standard_conflict", "component_conflict", "technical_conflict",
    "missing_dimension", "missing_pressure", "missing_material",
    "missing_standard", "missing_component"
]
NUMERIC_FEATURES = [
    "semantic_similarity", "lexical_similarity",
    "technical_attribute_overlap", "additional_attribute_count"
]


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
# DATA GENERATION (reuses exact Lane 7 pipeline)
# ---------------------------------------------------------------
def generate_diagnostic_data():
    master_df = pd.read_csv(SYNTHETIC_MASTER)
    gt_df     = pd.read_csv(SYNTHETIC_GT)

    mat_to_canon = dict(zip(master_df["material_id"].astype(str),
                            master_df["canonical_id"].astype(str)))
    mat_to_cpse  = dict(zip(master_df["material_id"].astype(str),
                            master_df["cpse_id"].astype(str)))
    mat_to_desc  = dict(zip(master_df["material_id"].astype(str),
                            master_df["description_original"].astype(str)))

    gt_map = {}
    for _, row in gt_df.iterrows():
        a, b = str(row["material_id_a"]), str(row["material_id_b"])
        rel  = row["relation_type"]
        gt_map.setdefault(a, {})[b] = rel
        gt_map.setdefault(b, {})[a] = rel

    # Retrieval infrastructure
    vector_store       = PostgresVectorStore()
    embedding_provider = Qwen3EmbeddingProvider()
    lexical_retriever  = BM25Retriever()
    db_materials       = vector_store.get_all_materials()
    lexical_retriever.refresh(db_materials)

    retrieval = RetrievalEngine(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever,
    )
    lane6    = PairFeatureEngine()
    pipeline = PreprocessingPipeline()
    ext_eng  = ExtractionEngine()

    # Build queries
    evaluation_queries = []
    for _, row in master_df.iterrows():
        prov = Provenance(
            source_system="SYNTHETIC",
            source_record_id=str(row["material_id"]),
            source_file="synthetic_generator",
            source_row=0,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="2.0",
            source_type="SYNTHETIC",
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code=str(row.get("material_code", "")),
            cpse=str(row.get("cpse_id", "")),
            original_description=str(row["description_original"]),
            canonical_uom=str(row.get("base_uom", "")),
        )
        evaluation_queries.append(record)

    # Material lookup
    print("Loading corpus for candidate mapping...")
    corpus_df = pd.read_csv(CORPUS_PATH)
    material_lookup = {}
    for idx, row in tqdm(corpus_df.iterrows(), total=len(corpus_df), desc="Parsing corpus"):
        mat_id = str(row["source_record_id"])
        prov = Provenance(
            source_type="REAL_PUBLIC_SOURCE",
            source_system=str(row.get("source_system", "UNKNOWN")),
            source_record_id=mat_id,
            source_file="cpse_material_corpus.csv",
            source_row=idx,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="1.0",
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code=str(row.get("original_material_code", "")),
            cpse=str(row.get("cpse", "")),
            original_description=str(row.get("original_description", "")),
            canonical_uom=str(row.get("canonical_uom", "")),
        )
        processed = ext_eng.process(pipeline.process_record(record))
        material_lookup[mat_id] = processed

    for q in evaluation_queries:
        processed_q = ext_eng.process(pipeline.process_record(q))
        material_lookup[q.provenance.source_record_id] = processed_q

    # Generate pairs
    all_rows = []
    print(f"Generating diagnostic data for {len(evaluation_queries)} queries...")
    for query in tqdm(evaluation_queries, desc="Diagnostic Gen"):
        q_id    = query.provenance.source_record_id
        q_canon = mat_to_canon.get(q_id, "CAN-UNKNOWN")
        q_cpse  = mat_to_cpse.get(q_id, "UNKNOWN")
        q_desc  = mat_to_desc.get(q_id, "")

        candidate_set = retrieval.retrieve_candidates(query, top_k=100)
        for cand in candidate_set.candidates:
            c_id = cand.material_id
            if c_id == q_id:
                continue
            c_mat = material_lookup.get(c_id)
            if c_mat is None:
                continue

            true_rel = gt_map.get(q_id, {}).get(c_id, "DISTINCT")

            pair = Pair(
                query_material=query,
                candidate_material=c_mat,
                semantic_similarity=cand.vector_similarity or 0.0,
                lexical_similarity=cand.bm25_score or 0.0,
            )

            result     = lane6.evaluate(pair)
            feat_dict  = extract_features(result)

            row = {
                "query_id": q_id,
                "candidate_id": c_id,
                "query_cpse": q_cpse,
                "candidate_cpse": c_mat.cpse or "",
                "query_desc": q_desc,
                "candidate_desc": c_mat.original_description or "",
                "true_relation": true_rel,
                "canonical_id": q_canon,
                "retrieval_rank": cand.retrieval_rank,
                # Lane 6 deterministic classification
                "lane6_relationship": result.relationship_class,
                "lane6_score": result.relationship_score,
                "lane6_explanation": "; ".join(result.explanation),
            }
            row.update(feat_dict)
            all_rows.append(row)

    return pd.DataFrame(all_rows)


# ---------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------
def run_diagnosis():
    # Phase 1: Generate or load diagnostic data
    print("Phase 1: Generating diagnostic dataset...")
    df = generate_diagnostic_data()
    print(f"Total pairs: {len(df)}")

    # Save full CSV
    os.makedirs("outputs", exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    # Phase 2: Load model and generate predictions
    print("Phase 2: Loading model and generating predictions...")
    ranker = Lane7Ranker()
    ranker.load(MODEL_DIR)

    X_all = df[FEATURE_NAMES].values
    all_probs = ranker.predict_proba(X_all)
    all_preds = np.argmax(all_probs, axis=1)

    df["predicted_relation"] = [CLASSES[p] for p in all_preds]
    for i, cls in enumerate(CLASSES):
        df[f"prob_{cls}"] = all_probs[:, i]

    # Re-save with predictions
    df.to_csv(OUT_CSV, index=False)

    # ============================================================
    # SECTION 1: CLASS DISTRIBUTION
    # ============================================================
    class_counts = dict(df["true_relation"].value_counts())
    total = len(df)
    class_proportions = {k: round(v / total, 6) for k, v in class_counts.items()}

    # ============================================================
    # SECTION 2: MODEL CONFIGURATION
    # ============================================================
    with open(os.path.join(MODEL_DIR, "metadata.json"), "r") as f:
        model_meta = json.load(f)

    config_analysis = {
        "params": model_meta["params"],
        "class_weights": "NONE -- no class_weight, is_unbalance, or scale_pos_weight configured",
        "num_boost_round": 500,
        "early_stopping": 20,
        "num_features": len(model_meta["feature_schema"]),
        "imbalance_handling": "NONE",
    }

    # ============================================================
    # SECTION 3: TRAIN/VAL/TEST SPLIT ANALYSIS
    # ============================================================
    print("Phase 3: Analyzing train/val/test splits...")
    features_list = [dict(row) for _, row in df[FEATURE_NAMES].iterrows()]
    labels = df["true_relation"].tolist()
    canonical_ids = df["canonical_id"].tolist()

    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        features_list, labels, canonical_ids, test_size=0.15, val_size=0.15
    )

    split_analysis = {}
    for name, y_split in [("train", y_train), ("val", y_val), ("test", y_test)]:
        counts = dict(Counter(y_split.tolist()))
        named_counts = {CLASSES[k]: v for k, v in counts.items()}
        split_analysis[name] = {
            "total": len(y_split),
            "class_counts": named_counts,
            "class_pct": {k: round(100 * v / max(1, len(y_split)), 2)
                          for k, v in named_counts.items()},
        }

    # ============================================================
    # SECTION 4: PER-CLASS FEATURE ANALYSIS
    # ============================================================
    print("Phase 4: Feature separability analysis...")
    minority_classes = ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]

    feature_separability = {}
    for rel in minority_classes:
        pos = df[df["true_relation"] == rel]
        neg = df[df["true_relation"] == "DISTINCT"]

        feat_comp = {}
        for feat in FEATURE_NAMES:
            pos_vals = pos[feat].dropna()
            neg_vals = neg[feat].dropna()

            if len(pos_vals) == 0:
                feat_comp[feat] = {"status": "NO_POSITIVE_DATA"}
                continue

            pos_mean = float(pos_vals.mean()) if len(pos_vals) > 0 else None
            neg_mean = float(neg_vals.mean()) if len(neg_vals) > 0 else None
            pos_median = float(pos_vals.median()) if len(pos_vals) > 0 else None
            neg_median = float(neg_vals.median()) if len(neg_vals) > 0 else None

            # Three-state: count True/False/None
            if feat in THREE_STATE_FEATURES:
                pos_all = pos[feat]
                neg_all = neg[feat]
                pos_true  = int((pos_all == 1.0).sum())
                pos_false = int((pos_all == 0.0).sum())
                pos_none  = int(pos_all.isna().sum())
                neg_true  = int((neg_all == 1.0).sum())
                neg_false = int((neg_all == 0.0).sum())
                neg_none  = int(neg_all.isna().sum())

                # Discriminative if positive class has significantly more True
                pos_true_rate = pos_true / max(1, len(pos_all))
                neg_true_rate = neg_true / max(1, len(neg_all))

                if pos_none / max(1, len(pos_all)) > 0.9 and neg_none / max(1, len(neg_all)) > 0.9:
                    disc = "UNAVAILABLE_CONSTANT"
                elif abs(pos_true_rate - neg_true_rate) > 0.15:
                    disc = "DISCRIMINATIVE"
                elif abs(pos_true_rate - neg_true_rate) > 0.05:
                    disc = "WEAKLY_DISCRIMINATIVE"
                else:
                    disc = "NON_DISCRIMINATIVE"

                feat_comp[feat] = {
                    "discriminative": disc,
                    "positive_true": pos_true, "positive_false": pos_false, "positive_none": pos_none,
                    "negative_true": neg_true, "negative_false": neg_false, "negative_none": neg_none,
                    "positive_true_rate": round(pos_true_rate, 4),
                    "negative_true_rate": round(neg_true_rate, 4),
                }
            else:
                # Numeric features
                if pos_mean is not None and neg_mean is not None:
                    diff = abs(pos_mean - neg_mean)
                    combined_std = float(pd.concat([pos_vals, neg_vals]).std())
                    if combined_std > 0:
                        effect_size = diff / combined_std
                    else:
                        effect_size = 0.0

                    if effect_size > 0.5:
                        disc = "DISCRIMINATIVE"
                    elif effect_size > 0.2:
                        disc = "WEAKLY_DISCRIMINATIVE"
                    else:
                        disc = "NON_DISCRIMINATIVE"
                else:
                    disc = "INSUFFICIENT_DATA"
                    effect_size = None

                feat_comp[feat] = {
                    "discriminative": disc,
                    "positive_mean": round(pos_mean, 4) if pos_mean else None,
                    "negative_mean": round(neg_mean, 4) if neg_mean else None,
                    "positive_median": round(pos_median, 4) if pos_median else None,
                    "negative_median": round(neg_median, 4) if neg_median else None,
                    "effect_size": round(effect_size, 4) if effect_size else None,
                }

        feature_separability[rel] = feat_comp

    # ============================================================
    # SECTION 5: PROBABILITY ANALYSIS
    # ============================================================
    print("Phase 5: Probability analysis...")
    prob_analysis = {}
    for rel in minority_classes:
        pos = df[df["true_relation"] == rel]
        if len(pos) == 0:
            prob_analysis[rel] = {"count": 0}
            continue

        prob_col = f"prob_{rel}"
        prob_distinct = "prob_DISTINCT"

        probs_self = pos[prob_col]
        probs_dist = pos[prob_distinct]

        # Case classification
        # Case 1: positive probability genuinely low (< 0.1)
        case1 = int((probs_self < 0.1).sum())
        # Case 2: positive probability decent (>= 0.1) but DISTINCT higher
        case2 = int(((probs_self >= 0.1) & (probs_dist > probs_self)).sum())
        # Case 3: positive probability highest but still predicted DISTINCT (shouldn't happen with argmax)
        case3 = int((probs_self >= probs_dist).sum()) - int((pos["predicted_relation"] == rel).sum())
        # Case 4: correctly predicted
        case4 = int((pos["predicted_relation"] == rel).sum())

        prob_analysis[rel] = {
            "count": int(len(pos)),
            "correctly_predicted": case4,
            "prob_genuinely_low_lt_0.1": case1,
            "prob_decent_but_distinct_higher": case2,
            "prob_highest_but_argmax_wrong": max(0, case3),
            "mean_self_probability": round(float(probs_self.mean()), 6),
            "median_self_probability": round(float(probs_self.median()), 6),
            "max_self_probability": round(float(probs_self.max()), 6),
            "mean_distinct_probability": round(float(probs_dist.mean()), 6),
            "median_distinct_probability": round(float(probs_dist.median()), 6),
        }

    # ============================================================
    # SECTION 6: REPRESENTATIVE EXAMPLES
    # ============================================================
    print("Phase 6: Generating representative examples...")
    examples = {}
    for rel in minority_classes:
        misclassified = df[(df["true_relation"] == rel) & (df["predicted_relation"] == "DISTINCT")]
        correctly_pred = df[(df["true_relation"] == rel) & (df["predicted_relation"] == rel)]

        mis_examples = []
        for _, row in misclassified.head(3).iterrows():
            mis_examples.append({
                "query_id": row["query_id"],
                "candidate_id": row["candidate_id"],
                "query_desc": row["query_desc"],
                "candidate_desc": row["candidate_desc"],
                "semantic_similarity": round(row["semantic_similarity"], 4),
                "lexical_similarity": round(row["lexical_similarity"], 4),
                "dimension_match": safe_json(row["dimension_match"]),
                "pressure_rating_match": safe_json(row["pressure_rating_match"]),
                "material_grade_match": safe_json(row["material_grade_match"]),
                "component_type_match": safe_json(row["component_type_match"]),
                "technical_conflict": bool(row["technical_conflict"]),
                "technical_attribute_overlap": int(row["technical_attribute_overlap"]),
                "additional_attribute_count": int(row["additional_attribute_count"]),
                "lane6_relationship": row["lane6_relationship"],
                "lane6_explanation": row["lane6_explanation"],
                "prob_IDENTICAL": round(row["prob_IDENTICAL"], 6),
                "prob_EQUIVALENT": round(row["prob_EQUIVALENT"], 6),
                "prob_VARIANT_OF": round(row["prob_VARIANT_OF"], 6),
                "prob_DISTINCT": round(row["prob_DISTINCT"], 6),
            })

        cor_examples = []
        for _, row in correctly_pred.head(2).iterrows():
            cor_examples.append({
                "query_id": row["query_id"],
                "candidate_id": row["candidate_id"],
                "semantic_similarity": round(row["semantic_similarity"], 4),
                "lexical_similarity": round(row["lexical_similarity"], 4),
                "dimension_match": safe_json(row["dimension_match"]),
                "pressure_rating_match": safe_json(row["pressure_rating_match"]),
                "material_grade_match": safe_json(row["material_grade_match"]),
                "lane6_relationship": row["lane6_relationship"],
                "prob_IDENTICAL": round(row["prob_IDENTICAL"], 6),
                "prob_EQUIVALENT": round(row["prob_EQUIVALENT"], 6),
                "prob_VARIANT_OF": round(row["prob_VARIANT_OF"], 6),
                "prob_DISTINCT": round(row["prob_DISTINCT"], 6),
            })

        examples[rel] = {
            "misclassified_as_DISTINCT": mis_examples,
            "correctly_predicted": cor_examples,
        }

    # ============================================================
    # SECTION 7: HARD NEGATIVE COMPARISON
    # ============================================================
    print("Phase 7: Hard negative comparison...")
    hard_neg_comparison = {}
    for rel in minority_classes:
        pos = df[df["true_relation"] == rel]
        neg = df[df["true_relation"] == "DISTINCT"]

        if len(pos) == 0:
            hard_neg_comparison[rel] = {"status": "NO_POSITIVE_DATA"}
            continue

        # Find DISTINCT pairs with similar semantic similarity to the positive pairs
        pos_sim_mean = pos["semantic_similarity"].mean()
        pos_sim_std  = pos["semantic_similarity"].std()
        sim_low  = pos_sim_mean - 1.5 * max(pos_sim_std, 0.01)
        sim_high = pos_sim_mean + 1.5 * max(pos_sim_std, 0.01)

        hard_negs = neg[(neg["semantic_similarity"] >= sim_low) & (neg["semantic_similarity"] <= sim_high)]

        comp = {}
        for feat in FEATURE_NAMES:
            pv = pos[feat].dropna()
            nv = hard_negs[feat].dropna()
            if len(pv) > 0 and len(nv) > 0:
                comp[feat] = {
                    "positive_mean": round(float(pv.mean()), 4),
                    "hard_negative_mean": round(float(nv.mean()), 4),
                    "difference": round(float(pv.mean() - nv.mean()), 4),
                }
            else:
                comp[feat] = {"positive_mean": None, "hard_negative_mean": None}

        hard_neg_comparison[rel] = {
            "positive_count": int(len(pos)),
            "hard_negative_count": int(len(hard_negs)),
            "sim_range": [round(sim_low, 4), round(sim_high, 4)],
            "feature_comparison": comp,
        }

    # ============================================================
    # SECTION 8: VARIANT_OF DEEP ANALYSIS
    # ============================================================
    print("Phase 8: VARIANT_OF deep analysis...")
    vof = df[df["true_relation"] == "VARIANT_OF"]
    vof_analysis = {
        "total": int(len(vof)),
        "predicted_as": dict(vof["predicted_relation"].value_counts()),
        "lane6_classified_as": dict(vof["lane6_relationship"].value_counts()),
        "additional_attribute_count_distribution": dict(vof["additional_attribute_count"].value_counts()),
        "technical_conflict_count": int(vof["technical_conflict"].sum()),
        "semantic_similarity_stats": {
            "mean": round(float(vof["semantic_similarity"].mean()), 4) if len(vof) > 0 else None,
            "median": round(float(vof["semantic_similarity"].median()), 4) if len(vof) > 0 else None,
            "min": round(float(vof["semantic_similarity"].min()), 4) if len(vof) > 0 else None,
            "max": round(float(vof["semantic_similarity"].max()), 4) if len(vof) > 0 else None,
        },
        "missingness": {
            feat: int(vof[feat].isna().sum()) for feat in THREE_STATE_FEATURES
        },
        "feature_none_rates": {
            feat: round(float(vof[feat].isna().sum()) / max(1, len(vof)), 4) for feat in THREE_STATE_FEATURES
        },
    }

    # ============================================================
    # SECTION 9: FEATURE IMPORTANCE
    # ============================================================
    importance_split = ranker.feature_importance()
    try:
        imp_gain = dict(zip(
            ranker.model.feature_name(),
            ranker.model.feature_importance(importance_type="gain")
        ))
    except Exception:
        imp_gain = {}

    # ============================================================
    # SECTION 10: MISSINGNESS SUMMARY
    # ============================================================
    missingness_summary = {}
    for feat in THREE_STATE_FEATURES:
        total_nan = int(df[feat].isna().sum())
        missingness_summary[feat] = {
            "total_missing": total_nan,
            "pct_missing": round(100 * total_nan / total, 2),
        }
        for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT"]:
            sub = df[df["true_relation"] == rel]
            sub_nan = int(sub[feat].isna().sum())
            missingness_summary[feat][f"{rel}_missing_pct"] = round(
                100 * sub_nan / max(1, len(sub)), 2
            )

    # ============================================================
    # SECTION 11: ROOT CAUSE DETERMINATION
    # ============================================================
    # Automated heuristic root cause classification
    root_causes = []
    evidence_items = []

    # A: Feature insufficiency?
    non_disc_count = 0
    unavail_count  = 0
    for rel in minority_classes:
        for feat, info in feature_separability.get(rel, {}).items():
            disc = info.get("discriminative", "")
            if disc == "NON_DISCRIMINATIVE":
                non_disc_count += 1
            if disc == "UNAVAILABLE_CONSTANT":
                unavail_count += 1

    if unavail_count > 10:
        root_causes.append("A_FEATURE_INSUFFICIENCY")
        evidence_items.append(
            f"{unavail_count} feature-class combinations are UNAVAILABLE/CONSTANT "
            f"(both positive and negative have >90% NaN)."
        )

    # B: Class imbalance?
    distinct_pct = class_proportions.get("DISTINCT", 0)
    if distinct_pct > 0.95:
        root_causes.append("B_CLASS_IMBALANCE")
        evidence_items.append(
            f"DISTINCT represents {distinct_pct*100:.1f}% of all pairs. "
            f"No class weights or is_unbalance configured in LightGBM."
        )

    # C: Model configuration?
    if "class_weight" not in str(model_meta["params"]) and "is_unbalance" not in str(model_meta["params"]):
        root_causes.append("C_MODEL_CONFIGURATION")
        evidence_items.append(
            "LightGBM has no class_weight, is_unbalance, or scale_pos_weight. "
            "The model has no incentive to predict minority classes."
        )

    # D: Probability/threshold?
    for rel in minority_classes:
        pa = prob_analysis.get(rel, {})
        if pa.get("count", 0) > 0 and pa.get("mean_self_probability", 0) < 0.05:
            root_causes.append("D_PROBABILITY_THRESHOLD")
            evidence_items.append(
                f"Mean P({rel}) for true {rel} pairs is {pa['mean_self_probability']:.6f} -- "
                f"the model assigns near-zero probability to the correct class."
            )
            break

    root_cause_classification = "MIXED" if len(root_causes) > 1 else (root_causes[0] if root_causes else "UNKNOWN")

    # ============================================================
    # SECTION 12: RECOMMENDATION
    # ============================================================
    if "A_FEATURE_INSUFFICIENCY" in root_causes and "B_CLASS_IMBALANCE" in root_causes:
        recommendation = (
            "DUAL ACTION REQUIRED: "
            "1. The feature space (Lane 6) has too many unavailable/constant features -- "
            "most structured attributes are NaN for >90% of pairs. The model cannot distinguish "
            "positive from negative using structured features alone. "
            "2. The training configuration has no class imbalance handling. "
            "RECOMMENDED SEQUENCE: "
            "Step 1: Add is_unbalance=True or class_weight to LightGBM and retrain (Lane 7 config fix). "
            "Step 2: If that is insufficient, improve Lane 6 feature extraction. "
            "Step 3: Proceed to Lane 8 decision/safety layer. "
            "Do NOT skip directly to Lane 8 without addressing the model training gap."
        )
    elif "B_CLASS_IMBALANCE" in root_causes:
        recommendation = (
            "FIX LANE 7 TRAINING CONFIGURATION. "
            "Add is_unbalance=True or class weights to LightGBM and retrain. "
            "The features may be sufficient but the model never learned minority classes."
        )
    elif "A_FEATURE_INSUFFICIENCY" in root_causes:
        recommendation = (
            "IMPROVE LANE 6 FEATURES. "
            "Current structured features are mostly NaN. "
            "Consider improving attribute extraction or adding normalized description comparison."
        )
    else:
        recommendation = (
            "INVESTIGATE FURTHER. The root cause is not clearly isolated. "
            "Consider per-class probability calibration analysis."
        )

    # ============================================================
    # ASSEMBLE REPORT
    # ============================================================
    report = {
        "1_class_distribution": {
            "counts": class_counts,
            "proportions": class_proportions,
            "total_pairs": total,
        },
        "2_model_configuration": config_analysis,
        "3_split_analysis": split_analysis,
        "4_feature_separability": feature_separability,
        "5_probability_analysis": prob_analysis,
        "6_representative_examples": examples,
        "7_hard_negative_comparison": hard_neg_comparison,
        "8_variant_of_deep_analysis": vof_analysis,
        "9_feature_importance": {
            "split": dict(sorted(importance_split.items(), key=lambda x: -x[1])),
            "gain": dict(sorted(imp_gain.items(), key=lambda x: -x[1])) if imp_gain else "unavailable",
        },
        "10_missingness_summary": missingness_summary,
        "11_root_cause": {
            "classification": root_cause_classification,
            "root_causes": root_causes,
            "evidence": evidence_items,
        },
        "12_recommendation": recommendation,
    }

    # ============================================================
    # WRITE JSON
    # ============================================================
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=safe_json)

    # ============================================================
    # WRITE TXT
    # ============================================================
    lines = []
    lines.append("=" * 72)
    lines.append("LANE 7C: LIGHTGBM MINORITY-CLASS FAILURE DIAGNOSIS")
    lines.append("UnifAI SIH26099")
    lines.append("=" * 72)

    lines.append("\n1. CLASS DISTRIBUTION")
    lines.append("-" * 40)
    for cls, cnt in sorted(class_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {cls:15s}: {cnt:>6d}  ({class_proportions[cls]*100:.2f}%)")

    lines.append("\n2. MODEL CONFIGURATION")
    lines.append("-" * 40)
    for k, v in config_analysis.items():
        lines.append(f"  {k}: {v}")

    lines.append("\n3. TRAIN/VAL/TEST SPLIT")
    lines.append("-" * 40)
    for split_name, info in split_analysis.items():
        lines.append(f"  {split_name}: {info['total']} pairs")
        for cls, pct in info["class_pct"].items():
            cnt = info["class_counts"].get(cls, 0)
            lines.append(f"    {cls:15s}: {cnt:>5d} ({pct:.2f}%)")

    lines.append("\n4. FEATURE SEPARABILITY (vs DISTINCT)")
    lines.append("-" * 40)
    for rel in minority_classes:
        lines.append(f"\n  {rel}:")
        for feat, info in feature_separability.get(rel, {}).items():
            disc = info.get("discriminative", "?")
            if "positive_mean" in info and info["positive_mean"] is not None:
                lines.append(f"    {feat:30s}: {disc:22s}  pos_mean={info['positive_mean']:.4f}  neg_mean={info.get('negative_mean', 0):.4f}")
            elif "positive_true_rate" in info:
                lines.append(f"    {feat:30s}: {disc:22s}  pos_true={info['positive_true_rate']:.4f}  neg_true={info['negative_true_rate']:.4f}")
            else:
                lines.append(f"    {feat:30s}: {disc}")

    lines.append("\n5. PROBABILITY ANALYSIS")
    lines.append("-" * 40)
    for rel in minority_classes:
        pa = prob_analysis.get(rel, {})
        if pa.get("count", 0) > 0:
            lines.append(f"  {rel} (n={pa['count']}):")
            lines.append(f"    Mean P({rel}): {pa['mean_self_probability']:.6f}")
            lines.append(f"    Median P({rel}): {pa['median_self_probability']:.6f}")
            lines.append(f"    Max P({rel}): {pa['max_self_probability']:.6f}")
            lines.append(f"    Mean P(DISTINCT): {pa['mean_distinct_probability']:.6f}")
            lines.append(f"    Correctly predicted: {pa['correctly_predicted']}")
            lines.append(f"    Prob genuinely low (<0.1): {pa['prob_genuinely_low_lt_0.1']}")
            lines.append(f"    Prob decent but DISTINCT higher: {pa['prob_decent_but_distinct_higher']}")

    lines.append("\n6. REPRESENTATIVE EXAMPLES")
    lines.append("-" * 40)
    for rel in minority_classes:
        exs = examples.get(rel, {}).get("misclassified_as_DISTINCT", [])
        if exs:
            lines.append(f"\n  TRUE={rel}, PREDICTED=DISTINCT:")
            for i, ex in enumerate(exs[:2]):
                lines.append(f"    Example {i+1}:")
                lines.append(f"      Query: {ex['query_desc'][:80]}")
                lines.append(f"      Cand:  {ex['candidate_desc'][:80]}")
                lines.append(f"      sim={ex['semantic_similarity']:.4f}  lex={ex['lexical_similarity']:.4f}")
                lines.append(f"      dim={ex['dimension_match']}  press={ex['pressure_rating_match']}  mat={ex['material_grade_match']}  comp={ex['component_type_match']}")
                lines.append(f"      conflict={ex['technical_conflict']}  overlap={ex['technical_attribute_overlap']}  extra={ex['additional_attribute_count']}")
                lines.append(f"      Lane6: {ex['lane6_relationship']}  |  {ex['lane6_explanation'][:80]}")
                lines.append(f"      P(IDENT)={ex['prob_IDENTICAL']:.6f}  P(EQUIV)={ex['prob_EQUIVALENT']:.6f}  P(VAR)={ex['prob_VARIANT_OF']:.6f}  P(DIST)={ex['prob_DISTINCT']:.6f}")

    lines.append("\n8. VARIANT_OF DEEP ANALYSIS")
    lines.append("-" * 40)
    for k, v in vof_analysis.items():
        if not isinstance(v, dict):
            lines.append(f"  {k}: {v}")
        else:
            lines.append(f"  {k}:")
            for kk, vv in v.items():
                lines.append(f"    {kk}: {vv}")

    lines.append("\n10. MISSINGNESS SUMMARY")
    lines.append("-" * 40)
    for feat, info in missingness_summary.items():
        lines.append(f"  {feat:30s}: {info['pct_missing']:.1f}% missing overall")

    lines.append("\n" + "=" * 72)
    lines.append("ROOT CAUSE CLASSIFICATION")
    lines.append("=" * 72)
    lines.append(f"\n  Classification: {root_cause_classification}")
    lines.append(f"  Root causes: {', '.join(root_causes)}")
    for ev in evidence_items:
        lines.append(f"  - {ev}")

    lines.append("\n" + "=" * 72)
    lines.append("RECOMMENDATION")
    lines.append("=" * 72)
    lines.append(f"\n  {recommendation}")

    lines.append("\n" + "=" * 72)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[-20:]))
    print(f"\nOutputs: {OUT_JSON}, {OUT_TXT}, {OUT_CSV}")


if __name__ == "__main__":
    run_diagnosis()
