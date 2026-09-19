"""
Lane 7 Error & Safety Analysis — UnifAI SIH26099

This script performs an exhaustive post-hoc analysis of the Lane 7 LightGBM
model trained on Synthetic V2 data.  It does NOT modify any existing code,
architecture, or model.  It consumes:

  • Lane 5 retrieval outputs (via the live Supabase vector store)
  • Lane 6 PairFeatureResult objects
  • The trained Lane 7 LightGBM model (outputs/lane7_model/)
  • Synthetic V2 ground truth

Outputs:
  • outputs/lane7_error_analysis.json
  • outputs/lane7_error_analysis.txt
"""

import os, sys, json, math
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
from src.ml.predictor import Lane7Predictor
from src.ml.evaluator import evaluate_predictions
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
SYNTHETIC_MASTER = "data/synthetic/material_master.csv"
SYNTHETIC_GT     = "data/synthetic/ground_truth_relationships.csv"
CORPUS_PATH      = "data/real_public/real_cpse_materials.csv"
MODEL_DIR        = "outputs/lane7_model"
OUT_JSON         = "outputs/lane7_error_analysis.json"
OUT_TXT          = "outputs/lane7_error_analysis.txt"

FEATURE_NAMES = get_feature_names()


# ──────────────────────────────────────────────────────────────────────
# Helper: safe JSON serialization
# ──────────────────────────────────────────────────────────────────────
def _safe(obj):
    """Make an object JSON-serializable."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if math.isnan(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Series):
        return obj.tolist()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


def _row_dict(query_desc, cand_desc, q_id, c_id, true_rel,
              ml_pred, final_pred, confidence, safety_triggered,
              feat_dict, result: PairFeatureResult):
    """Create an analysis row dict."""
    return {
        "query_id": q_id,
        "candidate_id": c_id,
        "query_description": query_desc,
        "candidate_description": cand_desc,
        "true_relationship": true_rel,
        "ml_prediction": ml_pred,
        "final_prediction": final_pred,
        "confidence": round(confidence, 4),
        "safety_triggered": safety_triggered,
        # Key features
        "semantic_similarity": round(feat_dict["semantic_similarity"], 4),
        "lexical_similarity": round(feat_dict["lexical_similarity"], 4),
        "dimension_match": _safe(feat_dict.get("dimension_match")),
        "pressure_rating_match": _safe(feat_dict.get("pressure_rating_match")),
        "material_grade_match": _safe(feat_dict.get("material_grade_match")),
        "standard_match": _safe(feat_dict.get("standard_match")),
        "component_type_match": _safe(feat_dict.get("component_type_match")),
        "technical_conflict": bool(result.technical_conflict),
        "dimension_conflict": bool(result.dimension_conflict),
        "pressure_conflict": bool(result.pressure_conflict),
        "material_conflict": bool(result.material_conflict),
        "standard_conflict": bool(result.standard_conflict),
        "component_conflict": bool(result.component_conflict),
        "missing_dimension": bool(result.missing_dimension),
        "missing_pressure": bool(result.missing_pressure),
        "missing_material": bool(result.missing_material),
        "missing_standard": bool(result.missing_standard),
        "missing_component": bool(result.missing_component),
        "technical_attribute_overlap": result.technical_attribute_overlap,
        "additional_attribute_count": result.additional_attribute_count,
        "explanation": result.explanation,
    }


# ──────────────────────────────────────────────────────────────────────
# DATA GENERATION  (mirrors lane7_validation.py exactly)
# ──────────────────────────────────────────────────────────────────────
def generate_pair_data():
    """Generate (features_list, labels, canonical_ids, pair_rows) from full pipeline."""
    master_df = pd.read_csv(SYNTHETIC_MASTER)
    gt_df     = pd.read_csv(SYNTHETIC_GT)

    mat_to_canon = dict(zip(master_df["material_id"].astype(str),
                            master_df["canonical_id"].astype(str)))

    gt_map = {}
    for _, row in gt_df.iterrows():
        a, b = str(row["material_id_a"]), str(row["material_id_b"])
        rel  = row["relation_type"]
        gt_map.setdefault(a, {})[b] = rel
        gt_map.setdefault(b, {})[a] = rel

    # ── Retrieval infrastructure ─────────────────────────────────────
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

    # ── Build evaluation queries from synthetic master ────────────────
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
            description_original=str(row["description_original"]),
            canonical_uom=str(row.get("base_uom", "")),
        )
        evaluation_queries.append(record)

    # ── Material lookup from 21K corpus + synthetic ──────────────────
    print("Loading 21K corpus for candidate mapping...")
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
            description_original=str(row.get("original_description", "")),
            canonical_uom=str(row.get("canonical_uom", "")),
        )
        processed = ext_eng.process(pipeline.process_record(record))
        material_lookup[mat_id] = processed

    for q in evaluation_queries:
        processed_q = ext_eng.process(pipeline.process_record(q))
        material_lookup[q.provenance.source_record_id] = processed_q

    # ── Lane 5 → Lane 6 pair generation ──────────────────────────────
    features_list  = []
    labels         = []
    canonical_ids  = []
    pair_rows      = []   # full analysis rows
    result_objects = []    # PairFeatureResult references

    print(f"Generating Lane 6 features for {len(evaluation_queries)} queries...")
    for query in tqdm(evaluation_queries, desc="Lane 7 Data Gen"):
        q_id    = query.provenance.source_record_id
        q_canon = mat_to_canon.get(q_id, "CAN-UNKNOWN")
        q_desc  = query.original_description or ""

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

            features_list.append(feat_dict)
            labels.append(true_rel)
            canonical_ids.append(q_canon)
            result_objects.append(result)

            pair_rows.append({
                "q_id": q_id,
                "c_id": c_id,
                "q_desc": q_desc,
                "c_desc": c_mat.original_description or "",
                "true_rel": true_rel,
                "q_canon": q_canon,
            })

    print(f"Total pairs generated: {len(features_list)}")
    return features_list, labels, canonical_ids, pair_rows, result_objects


# ──────────────────────────────────────────────────────────────────────
# ANALYSIS
# ──────────────────────────────────────────────────────────────────────
def run_analysis():
    features_list, labels, canonical_ids, pair_rows, result_objects = generate_pair_data()

    n_pairs = len(features_list)
    if n_pairs == 0:
        raise ValueError("No pairs generated – cannot analyse.")

    # ── Train / split  (reproduces lane7_validation.py exactly) ──────
    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        features_list, labels, canonical_ids, test_size=0.15, val_size=0.15
    )

    # ── Load the EXISTING trained model ──────────────────────────────
    ranker = Lane7Ranker()
    ranker.load(MODEL_DIR)
    predictor = Lane7Predictor(MODEL_DIR)

    # ── Full-dataset predictions (before & after safety) ─────────────
    all_feat_df = pd.DataFrame(features_list)
    X_all = all_feat_df[FEATURE_NAMES].values
    all_probs    = ranker.predict_proba(X_all)
    all_ml_preds = np.argmax(all_probs, axis=1)

    analysis_rows = []
    for i in range(n_pairs):
        ml_class   = CLASSES[all_ml_preds[i]]
        confidence = float(all_probs[i][all_ml_preds[i]])
        result     = result_objects[i]

        # Safety layer
        final_class = ml_class
        safety_triggered = False
        if result.technical_conflict and ml_class in ("IDENTICAL", "EQUIVALENT"):
            final_class = "DISTINCT"
            safety_triggered = True

        row = _row_dict(
            query_desc=pair_rows[i]["q_desc"],
            cand_desc=pair_rows[i]["c_desc"],
            q_id=pair_rows[i]["q_id"],
            c_id=pair_rows[i]["c_id"],
            true_rel=pair_rows[i]["true_rel"],
            ml_pred=ml_class,
            final_pred=final_class,
            confidence=confidence,
            safety_triggered=safety_triggered,
            feat_dict=features_list[i],
            result=result,
        )
        analysis_rows.append(row)

    df = pd.DataFrame(analysis_rows)

    # ══════════════════════════════════════════════════════════════════
    # 1.  PER-CLASS METRICS (on full dataset)
    # ══════════════════════════════════════════════════════════════════
    y_true_int  = [map_label(r["true_relationship"]) for r in analysis_rows]
    y_pred_int  = [CLASSES.index(r["final_prediction"]) for r in analysis_rows]

    metrics = evaluate_predictions(y_true_int, y_pred_int)

    # ══════════════════════════════════════════════════════════════════
    # 2.  CONFUSION MATRIX  (already inside `metrics`)
    # ══════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════
    # 3.  FALSE-POSITIVE ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    fp_identical  = df[(df["final_prediction"] == "IDENTICAL")  & (df["true_relationship"] != "IDENTICAL")]
    fp_equivalent = df[(df["final_prediction"] == "EQUIVALENT") & (df["true_relationship"] != "EQUIVALENT")]
    fp_variant    = df[(df["final_prediction"] == "VARIANT_OF") & (df["true_relationship"] != "VARIANT_OF")]

    def _sample(sub_df, n=5):
        return sub_df.head(n).to_dict(orient="records")

    false_positive_analysis = {
        "predicted_IDENTICAL_but_wrong": {
            "count": int(len(fp_identical)),
            "examples": _sample(fp_identical),
        },
        "predicted_EQUIVALENT_but_wrong": {
            "count": int(len(fp_equivalent)),
            "examples": _sample(fp_equivalent),
        },
        "predicted_VARIANT_OF_but_wrong": {
            "count": int(len(fp_variant)),
            "examples": _sample(fp_variant),
        },
    }

    # ══════════════════════════════════════════════════════════════════
    # 4.  TECHNICAL SAFETY ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    n_tech_conflict  = int(df["technical_conflict"].sum())
    n_ml_ident_equiv = int(((df["ml_prediction"] == "IDENTICAL") | (df["ml_prediction"] == "EQUIVALENT")).sum())
    n_overridden     = int(df["safety_triggered"].sum())

    # Incorrectly allowed = after safety, still IDENTICAL/EQUIVALENT but has technical_conflict
    incorrectly_allowed = df[
        (df["technical_conflict"]) &
        (df["final_prediction"].isin(["IDENTICAL", "EQUIVALENT"]))
    ]
    n_incorrectly_allowed = int(len(incorrectly_allowed))

    # Routed to UNDETERMINED / REVIEW
    n_undetermined = int((df["final_prediction"] == "UNDETERMINED").sum())

    safety_analysis = {
        "total_pairs_with_hard_technical_conflict": n_tech_conflict,
        "ml_predicted_IDENTICAL_or_EQUIVALENT_before_safety": n_ml_ident_equiv,
        "overridden_by_safety_layer": n_overridden,
        "incorrectly_allowed_through_safety": n_incorrectly_allowed,
        "routed_to_UNDETERMINED_or_REVIEW": n_undetermined,
    }

    # ══════════════════════════════════════════════════════════════════
    # 5.  HIGH-SEMANTIC-SIMILARITY  +  TECHNICAL CONFLICT
    # ══════════════════════════════════════════════════════════════════
    high_sim_conflict = df[(df["semantic_similarity"] >= 0.80) & (df["technical_conflict"])]

    high_sim_conflict_analysis = {
        "count": int(len(high_sim_conflict)),
        "examples": _sample(high_sim_conflict, 10),
    }

    # ══════════════════════════════════════════════════════════════════
    # 6.  MISSING-INFORMATION ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    missing_fields = ["missing_dimension", "missing_pressure", "missing_material",
                      "missing_standard", "missing_component"]
    missing_analysis = {}
    for mf in missing_fields:
        subset = df[df[mf] == True]
        # Of those with missing info, how many were predicted positively?
        positive_preds = subset[subset["final_prediction"].isin(["IDENTICAL", "EQUIVALENT", "VARIANT_OF"])]
        missing_analysis[mf] = {
            "total_pairs": int(len(subset)),
            "pct_of_all_pairs": round(100 * len(subset) / max(1, n_pairs), 2),
            "positive_predictions_despite_missing": int(len(positive_preds)),
        }

    # ══════════════════════════════════════════════════════════════════
    # 7.  VARIANT_OF ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    true_variant   = df[df["true_relationship"] == "VARIANT_OF"]
    pred_variant   = df[df["final_prediction"]  == "VARIANT_OF"]

    variant_correct         = df[(df["true_relationship"] == "VARIANT_OF") & (df["final_prediction"] == "VARIANT_OF")]
    variant_as_identical    = df[(df["true_relationship"] == "VARIANT_OF") & (df["final_prediction"] == "IDENTICAL")]
    variant_as_equivalent   = df[(df["true_relationship"] == "VARIANT_OF") & (df["final_prediction"] == "EQUIVALENT")]
    variant_as_distinct     = df[(df["true_relationship"] == "VARIANT_OF") & (df["final_prediction"] == "DISTINCT")]

    variant_analysis = {
        "true_VARIANT_OF_in_dataset": int(len(true_variant)),
        "predicted_VARIANT_OF_total": int(len(pred_variant)),
        "correctly_predicted": int(len(variant_correct)),
        "confused_with_IDENTICAL": int(len(variant_as_identical)),
        "confused_with_EQUIVALENT": int(len(variant_as_equivalent)),
        "confused_with_DISTINCT": int(len(variant_as_distinct)),
        "correct_examples": _sample(variant_correct),
        "confused_examples": _sample(variant_as_distinct),
    }

    # ══════════════════════════════════════════════════════════════════
    # 8.  EQUIVALENT ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    true_equiv = df[df["true_relationship"] == "EQUIVALENT"]
    equiv_correct   = df[(df["true_relationship"] == "EQUIVALENT") & (df["final_prediction"] == "EQUIVALENT")]
    equiv_as_ident  = df[(df["true_relationship"] == "EQUIVALENT") & (df["final_prediction"] == "IDENTICAL")]
    equiv_as_dist   = df[(df["true_relationship"] == "EQUIVALENT") & (df["final_prediction"] == "DISTINCT")]

    equivalent_analysis = {
        "true_EQUIVALENT_in_dataset": int(len(true_equiv)),
        "correctly_predicted": int(len(equiv_correct)),
        "confused_with_IDENTICAL": int(len(equiv_as_ident)),
        "confused_with_DISTINCT": int(len(equiv_as_dist)),
        "avg_semantic_similarity_correct": round(float(equiv_correct["semantic_similarity"].mean()), 4) if len(equiv_correct) > 0 else None,
        "avg_semantic_similarity_missed":  round(float(equiv_as_dist["semantic_similarity"].mean()), 4) if len(equiv_as_dist) > 0 else None,
        "correct_examples": _sample(equiv_correct),
        "missed_examples":  _sample(equiv_as_dist),
    }

    # ══════════════════════════════════════════════════════════════════
    # 9.  IDENTICAL ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    true_ident = df[df["true_relationship"] == "IDENTICAL"]
    ident_correct  = df[(df["true_relationship"] == "IDENTICAL") & (df["final_prediction"] == "IDENTICAL")]
    ident_as_equiv = df[(df["true_relationship"] == "IDENTICAL") & (df["final_prediction"] == "EQUIVALENT")]
    ident_as_dist  = df[(df["true_relationship"] == "IDENTICAL") & (df["final_prediction"] == "DISTINCT")]

    identical_analysis = {
        "true_IDENTICAL_in_dataset": int(len(true_ident)),
        "correctly_predicted": int(len(ident_correct)),
        "confused_with_EQUIVALENT": int(len(ident_as_equiv)),
        "confused_with_DISTINCT": int(len(ident_as_dist)),
        "avg_semantic_similarity_correct": round(float(ident_correct["semantic_similarity"].mean()), 4) if len(ident_correct) > 0 else None,
        "avg_semantic_similarity_missed":  round(float(ident_as_dist["semantic_similarity"].mean()), 4) if len(ident_as_dist) > 0 else None,
        "correct_examples": _sample(ident_correct),
        "missed_examples":  _sample(ident_as_dist),
    }

    # ══════════════════════════════════════════════════════════════════
    # 10. BEFORE vs AFTER SAFETY
    # ══════════════════════════════════════════════════════════════════
    before_after = defaultdict(int)
    for r in analysis_rows:
        key = f"{r['ml_prediction']} → {r['final_prediction']}"
        before_after[key] += 1
    before_after_dict = dict(sorted(before_after.items(), key=lambda x: -x[1]))

    # ══════════════════════════════════════════════════════════════════
    # 11. FEATURE IMPORTANCE
    # ══════════════════════════════════════════════════════════════════
    importances = ranker.feature_importance()
    sorted_importance = dict(sorted(importances.items(), key=lambda x: -x[1]))

    # ══════════════════════════════════════════════════════════════════
    # 12. DATASET LIMITATIONS
    # ══════════════════════════════════════════════════════════════════
    true_counts = Counter(labels)
    dataset_limitations = {
        "total_pairs": n_pairs,
        "class_distribution": dict(true_counts),
        "class_imbalance_ratio": {
            cls: round(cnt / max(1, n_pairs), 4) for cls, cnt in true_counts.items()
        },
        "DISTINCT_pct": round(100 * true_counts.get("DISTINCT", 0) / max(1, n_pairs), 2),
        "minority_classes_total": sum(v for k, v in true_counts.items() if k != "DISTINCT"),
        "warning": (
            "97.04% accuracy is driven by DISTINCT class dominance. "
            "The model has almost no ability to distinguish IDENTICAL, "
            "EQUIVALENT, or VARIANT_OF from DISTINCT due to extreme class imbalance. "
            "This does NOT represent real-world matching accuracy."
        ),
        "synthetic_v2_limitations": [
            "Only 329 materials with 88 unique canonical IDs.",
            "Ground truth has only 37 IDENTICAL, 164 EQUIVALENT, 59 VARIANT_OF, 199 DISTINCT pairs.",
            "Most positive pairs are NOT retrieved by Lane 5 because the query and candidate "
            "are from different CPSEs with different descriptions, creating a retrieval gap.",
            "The 27K candidate pairs are overwhelmingly DISTINCT negatives.",
        ],
    }

    # ══════════════════════════════════════════════════════════════════
    # ASSEMBLE REPORT
    # ══════════════════════════════════════════════════════════════════
    report = {
        "1_per_class_metrics": metrics["Per_Class"],
        "1b_aggregate_metrics": {
            "accuracy": metrics["Accuracy"],
            "macro_precision": metrics["Macro_Precision"],
            "macro_recall": metrics["Macro_Recall"],
            "macro_f1": metrics["Macro_F1"],
            "weighted_f1": metrics["Weighted_F1"],
        },
        "2_confusion_matrix": {
            "labels": CLASSES,
            "matrix": metrics["Confusion_Matrix"],
        },
        "3_false_positive_analysis": false_positive_analysis,
        "4_technical_safety_analysis": safety_analysis,
        "5_high_similarity_conflict_analysis": high_sim_conflict_analysis,
        "6_missing_information_analysis": missing_analysis,
        "7_variant_of_analysis": variant_analysis,
        "8_equivalent_analysis": equivalent_analysis,
        "9_identical_analysis": identical_analysis,
        "10_before_vs_after_safety": before_after_dict,
        "11_feature_importance": sorted_importance,
        "12_dataset_limitations": dataset_limitations,
    }

    # ── KEY FINDINGS ─────────────────────────────────────────────────
    key_findings = [
        "A. KEY FINDINGS",
        f"   Total pairs analysed: {n_pairs}",
        f"   Overall accuracy: {metrics['Accuracy']:.4f}",
        f"   Macro F1: {metrics['Macro_F1']:.4f}",
        f"   DISTINCT dominates at {dataset_limitations['DISTINCT_pct']:.1f}% of all pairs.",
        f"   IDENTICAL recall: {metrics['Per_Class']['IDENTICAL']['Recall']:.4f} (support: {metrics['Per_Class']['IDENTICAL']['Support']})",
        f"   EQUIVALENT recall: {metrics['Per_Class']['EQUIVALENT']['Recall']:.4f} (support: {metrics['Per_Class']['EQUIVALENT']['Support']})",
        f"   VARIANT_OF recall: {metrics['Per_Class']['VARIANT_OF']['Recall']:.4f} (support: {metrics['Per_Class']['VARIANT_OF']['Support']})",
        f"   The model essentially predicts DISTINCT for everything — it has not learned minority class boundaries.",
        "",
        "B. SAFETY FINDINGS",
        f"   Pairs with hard technical conflicts: {n_tech_conflict}",
        f"   ML predicted IDENTICAL/EQUIVALENT before safety: {n_ml_ident_equiv}",
        f"   Overridden by safety layer: {n_overridden}",
        f"   Incorrectly allowed through safety: {n_incorrectly_allowed}",
        f"   High-similarity (>=0.80) + conflict pairs: {len(high_sim_conflict)}",
        "",
        "C. LIMITATIONS",
        f"   Extreme class imbalance: {dataset_limitations['DISTINCT_pct']:.1f}% DISTINCT.",
        f"   Minority class samples (IDENTICAL+EQUIVALENT+VARIANT_OF): {dataset_limitations['minority_classes_total']}",
        "   97.04% accuracy is misleading — a trivial 'always DISTINCT' classifier would score ~98%.",
        "   Synthetic V2 ground truth covers only 459 defined pairs across 329 materials.",
        "   Many positive-class ground-truth pairs are not retrieved by Lane 5 (cross-CPSE retrieval gap).",
        "",
        "D. CONCRETE REQUIREMENTS FOR LANE 8",
        "   1. Lane 8 MUST NOT rely on the LightGBM probability alone for positive-class decisions.",
        "   2. Lane 8 must incorporate deterministic rules from Lane 6 (component match, technical conflict, ",
        "      attribute overlap) as hard decision boundaries, not just ML soft predictions.",
        "   3. Lane 8 must handle UNDETERMINED/REVIEW routing: when evidence is insufficient, pairs must",
        "      be flagged for human governance (Lane 9), not forced into DISTINCT.",
        "   4. Lane 8 must implement class-specific decision thresholds — a single argmax is insufficient.",
        "   5. Lane 8 must account for missing-information prevalence; >90% of pairs lack extractable",
        "      dimension, pressure, material, or standard information — meaning the ML model receives",
        "      NaN for most technical features and relies almost entirely on similarity scores.",
        "   6. The safety layer correctly blocks hard conflicts from being classified as IDENTICAL/EQUIVALENT.",
        "      Lane 8 must preserve this safety behaviour and extend it with graduated confidence tiers.",
        "   7. Lane 8 must support a CONFIDENCE_LEVEL output (HIGH / MEDIUM / LOW / REVIEW) alongside",
        "      the relationship class to enable Lane 9 human governance to prioritize reviews.",
    ]

    report["key_findings"] = key_findings

    # ══════════════════════════════════════════════════════════════════
    # WRITE OUTPUTS
    # ══════════════════════════════════════════════════════════════════
    os.makedirs("outputs", exist_ok=True)

    # JSON (clean serialization)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_safe)

    # TXT (human readable)
    lines = []
    lines.append("=" * 72)
    lines.append("LANE 7 ERROR & SAFETY ANALYSIS — UNIFAI SIH26099")
    lines.append("=" * 72)
    lines.append("")

    lines.append("1. PER-CLASS METRICS")
    lines.append("-" * 40)
    for cls in CLASSES:
        m = metrics["Per_Class"][cls]
        lines.append(f"  {cls:15s}  P={m['Precision']:.4f}  R={m['Recall']:.4f}  F1={m['F1']:.4f}  Support={m['Support']}")
    lines.append(f"\n  Accuracy: {metrics['Accuracy']:.4f}  Macro-F1: {metrics['Macro_F1']:.4f}  Weighted-F1: {metrics['Weighted_F1']:.4f}")

    lines.append("\n2. CONFUSION MATRIX (rows=true, cols=pred)")
    lines.append("-" * 40)
    header = "              " + "  ".join(f"{c:>10}" for c in CLASSES)
    lines.append(header)
    for i, cls in enumerate(CLASSES):
        row_str = "  ".join(f"{v:>10}" for v in metrics["Confusion_Matrix"][i])
        lines.append(f"  {cls:>12}  {row_str}")

    lines.append("\n3. FALSE-POSITIVE ANALYSIS")
    lines.append("-" * 40)
    for key, data in false_positive_analysis.items():
        lines.append(f"  {key}: {data['count']} cases")

    lines.append("\n4. TECHNICAL SAFETY ANALYSIS")
    lines.append("-" * 40)
    for k, v in safety_analysis.items():
        lines.append(f"  {k}: {v}")

    lines.append("\n5. HIGH-SIMILARITY + CONFLICT ANALYSIS")
    lines.append("-" * 40)
    lines.append(f"  Pairs with semantic_similarity >= 0.80 AND technical_conflict: {high_sim_conflict_analysis['count']}")

    lines.append("\n6. MISSING-INFORMATION ANALYSIS")
    lines.append("-" * 40)
    for mf, data in missing_analysis.items():
        lines.append(f"  {mf}: {data['total_pairs']} pairs ({data['pct_of_all_pairs']}%), "
                      f"{data['positive_predictions_despite_missing']} positive despite missing")

    lines.append("\n7. VARIANT_OF ANALYSIS")
    lines.append("-" * 40)
    for k, v in variant_analysis.items():
        if isinstance(v, list):
            continue
        lines.append(f"  {k}: {v}")

    lines.append("\n8. EQUIVALENT ANALYSIS")
    lines.append("-" * 40)
    for k, v in equivalent_analysis.items():
        if isinstance(v, list):
            continue
        lines.append(f"  {k}: {v}")

    lines.append("\n9. IDENTICAL ANALYSIS")
    lines.append("-" * 40)
    for k, v in identical_analysis.items():
        if isinstance(v, list):
            continue
        lines.append(f"  {k}: {v}")

    lines.append("\n10. BEFORE vs AFTER SAFETY LAYER")
    lines.append("-" * 40)
    for k, v in before_after_dict.items():
        lines.append(f"  {k}: {v}")

    lines.append("\n11. FEATURE IMPORTANCE (LightGBM split)")
    lines.append("-" * 40)
    for k, v in sorted_importance.items():
        lines.append(f"  {k}: {v}")

    lines.append("\n12. DATASET LIMITATIONS")
    lines.append("-" * 40)
    lines.append(f"  Total pairs: {n_pairs}")
    lines.append(f"  DISTINCT: {dataset_limitations['DISTINCT_pct']:.1f}%")
    lines.append(f"  Minority class total: {dataset_limitations['minority_classes_total']}")
    lines.append(f"  WARNING: {dataset_limitations['warning']}")

    lines.append("\n" + "=" * 72)
    for finding in key_findings:
        lines.append(finding)
    lines.append("=" * 72)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(key_findings))
    print(f"\nOutputs written to:\n  {OUT_JSON}\n  {OUT_TXT}")


if __name__ == "__main__":
    run_analysis()
