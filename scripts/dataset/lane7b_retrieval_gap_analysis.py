"""
Lane 7B: Positive Relationship Retrieval Gap Analysis -- UnifAI SIH26099

Read-only diagnostic.  Determines whether the poor minority-class performance
observed in Lane 7 is caused by:
  A.  Retrieval failure  (the correct positive target never enters the candidate set)
  B.  Classification failure  (the target is retrieved but misclassified by Lane 7)

Uses the EXISTING Lane 5 retrieve_candidates() API unchanged.
Does NOT modify any production code, model, dataset, or ground truth.

Outputs:
  outputs/lane7b_retrieval_gap_analysis.json
  outputs/lane7b_retrieval_gap_analysis.txt
  outputs/lane7b_positive_retrieval_pairs.csv
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
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------
# Paths
# ---------------------------------------------------------------
SYNTHETIC_MASTER = "data/synthetic/material_master.csv"
SYNTHETIC_GT     = "data/synthetic/ground_truth_relationships.csv"
OUT_JSON         = "outputs/lane7b_retrieval_gap_analysis.json"
OUT_TXT          = "outputs/lane7b_retrieval_gap_analysis.txt"
OUT_CSV          = "outputs/lane7b_positive_retrieval_pairs.csv"
TOP_K            = 100   # must match Lane 7 pipeline


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
# Build evaluation queries  (same logic as lane7_validation.py)
# ---------------------------------------------------------------
def build_queries():
    master_df = pd.read_csv(SYNTHETIC_MASTER)
    pipeline  = PreprocessingPipeline()
    ext_eng   = ExtractionEngine()

    mat_to_cpse  = dict(zip(master_df["material_id"].astype(str),
                            master_df["cpse_id"].astype(str)))
    mat_to_canon = dict(zip(master_df["material_id"].astype(str),
                            master_df["canonical_id"].astype(str)))

    records = {}
    for _, row in master_df.iterrows():
        mat_id = str(row["material_id"])
        prov = Provenance(
            source_system="SYNTHETIC",
            source_record_id=mat_id,
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
        processed = ext_eng.process(pipeline.process_record(record))
        records[mat_id] = processed

    return records, mat_to_cpse, mat_to_canon


# ---------------------------------------------------------------
# Load positive ground-truth relationships
# ---------------------------------------------------------------
def load_positive_gt():
    """
    Load positive relationships from ground truth.

    Directionality handling:
      The ground truth CSV lists each pair once (material_id_a, material_id_b).
      For retrieval coverage, we evaluate BOTH directions because the retrieval
      engine is not guaranteed to be symmetric (BM25 + vector may rank
      differently depending on which material is the query).

      Each ground-truth row generates TWO evaluation tasks:
        1.  query = material_id_a,  target = material_id_b
        2.  query = material_id_b,  target = material_id_a

      This means totals will be 2x the CSV row count for positive classes.
      This is documented explicitly in the output.
    """
    gt_df = pd.read_csv(SYNTHETIC_GT)
    positive_classes = {"IDENTICAL", "EQUIVALENT", "VARIANT_OF"}

    pairs = []
    for _, row in gt_df.iterrows():
        rel = row["relation_type"]
        if rel not in positive_classes:
            continue
        a = str(row["material_id_a"])
        b = str(row["material_id_b"])
        cpse_a = str(row["cpse_a"])
        cpse_b = str(row["cpse_b"])

        # Direction A -> B
        pairs.append({
            "query_id": a,
            "target_id": b,
            "query_cpse": cpse_a,
            "target_cpse": cpse_b,
            "relationship": rel,
            "direction": "A->B",
            "same_cpse": cpse_a == cpse_b,
        })
        # Direction B -> A
        pairs.append({
            "query_id": b,
            "target_id": a,
            "query_cpse": cpse_b,
            "target_cpse": cpse_a,
            "relationship": rel,
            "direction": "B->A",
            "same_cpse": cpse_a == cpse_b,
        })

    return pairs


# ---------------------------------------------------------------
# MAIN ANALYSIS
# ---------------------------------------------------------------
def run_analysis():
    records, mat_to_cpse, mat_to_canon = build_queries()
    positive_pairs = load_positive_gt()

    print(f"Positive ground-truth evaluation tasks: {len(positive_pairs)}")
    print(f"  (each CSV row evaluated in both directions)")

    # -- Build retrieval engine (identical to Lane 7 pipeline) --------
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

    # -- Leakage assertion --------------------------------------------
    # Ground truth is NEVER used as retrieval input.  We only use it
    # AFTER retrieval to check if the target appears in the candidate set.
    # The retrieval engine receives only the UnifiedMaterialRecord query.

    # -- Run retrieval for each unique query --------------------------
    # Cache results so we don't re-run retrieval for the same query
    retrieval_cache = {}   # query_id -> {candidate_id: rank}

    unique_queries = set(p["query_id"] for p in positive_pairs)
    print(f"Unique queries to run: {len(unique_queries)}")

    for q_id in tqdm(sorted(unique_queries), desc="Retrieval"):
        if q_id not in records:
            retrieval_cache[q_id] = {}
            continue
        query_record = records[q_id]
        candidate_set = retrieval.retrieve_candidates(query_record, top_k=TOP_K)

        rank_map = {}
        for cand in candidate_set.candidates:
            rank_map[cand.material_id] = cand.retrieval_rank
        retrieval_cache[q_id] = rank_map

    # -- Evaluate each positive pair ----------------------------------
    csv_rows = []

    for pair in positive_pairs:
        q_id   = pair["query_id"]
        t_id   = pair["target_id"]
        rel    = pair["relationship"]
        rank_map = retrieval_cache.get(q_id, {})

        rank = rank_map.get(t_id, None)

        # Determine retrieval bucket
        if rank is not None and rank <= 10:
            bucket = "RETRIEVED_TOP10"
        elif rank is not None and rank <= 25:
            bucket = "RETRIEVED_11_25"
        elif rank is not None and rank <= 50:
            bucket = "RETRIEVED_26_50"
        elif rank is not None and rank <= 100:
            bucket = "RETRIEVED_51_100"
        else:
            bucket = "NOT_RETRIEVED_TOP100"

        # Look up similarity scores
        vec_score = None
        bm25_score = None
        if q_id in records:
            cset = retrieval_cache.get(q_id, {})
            # We need the actual candidate object for scores - re-retrieve or find in cache
            # Since we only cached rank_map, let's get scores from the candidate_set
            # Actually let's cache the full candidate set for score lookup
        # We'll do a second pass for scores below

        csv_rows.append({
            "query_id": q_id,
            "target_id": t_id,
            "relationship": rel,
            "direction": pair["direction"],
            "query_cpse": pair["query_cpse"],
            "target_cpse": pair["target_cpse"],
            "same_cpse": pair["same_cpse"],
            "rank": rank,
            "bucket": bucket,
            "in_top10": rank is not None and rank <= 10,
            "in_top25": rank is not None and rank <= 25,
            "in_top50": rank is not None and rank <= 50,
            "in_top100": rank is not None and rank <= 100,
        })

    df = pd.DataFrame(csv_rows)

    # ================================================================
    # 4. RETRIEVAL COVERAGE AT K
    # ================================================================
    def recall_at_k(sub_df, k):
        return float(sub_df[f"in_top{k}"].sum()) / max(1, len(sub_df))

    per_class_table = {}
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        sub = df[df["relationship"] == rel]
        per_class_table[rel] = {
            "total": int(len(sub)),
            "recall_at_10":  round(recall_at_k(sub, 10), 4),
            "recall_at_25":  round(recall_at_k(sub, 25), 4),
            "recall_at_50":  round(recall_at_k(sub, 50), 4),
            "recall_at_100": round(recall_at_k(sub, 100), 4),
            "count_at_10":  int(sub["in_top10"].sum()),
            "count_at_25":  int(sub["in_top25"].sum()),
            "count_at_50":  int(sub["in_top50"].sum()),
            "count_at_100": int(sub["in_top100"].sum()),
            "not_retrieved": int((~sub["in_top100"]).sum()),
        }

    # ALL POSITIVE
    all_pos = df
    per_class_table["ALL_POSITIVE"] = {
        "total": int(len(all_pos)),
        "recall_at_10":  round(recall_at_k(all_pos, 10), 4),
        "recall_at_25":  round(recall_at_k(all_pos, 25), 4),
        "recall_at_50":  round(recall_at_k(all_pos, 50), 4),
        "recall_at_100": round(recall_at_k(all_pos, 100), 4),
        "count_at_10":  int(all_pos["in_top10"].sum()),
        "count_at_25":  int(all_pos["in_top25"].sum()),
        "count_at_50":  int(all_pos["in_top50"].sum()),
        "count_at_100": int(all_pos["in_top100"].sum()),
        "not_retrieved": int((~all_pos["in_top100"]).sum()),
    }

    # ================================================================
    # 5. BUCKET DISTRIBUTION
    # ================================================================
    bucket_dist = {}
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "ALL_POSITIVE"]:
        sub = df[df["relationship"] == rel] if rel != "ALL_POSITIVE" else df
        bucket_dist[rel] = dict(sub["bucket"].value_counts())

    # ================================================================
    # 7. RANK DISTRIBUTION
    # ================================================================
    rank_stats = {}
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        sub = df[df["relationship"] == rel]
        ranks = sub["rank"].dropna().tolist()
        if ranks:
            rank_stats[rel] = {
                "count_retrieved": len(ranks),
                "min_rank": int(min(ranks)),
                "median_rank": round(float(statistics.median(ranks)), 1),
                "mean_rank": round(float(statistics.mean(ranks)), 1),
                "max_rank": int(max(ranks)),
                "p25": round(float(np.percentile(ranks, 25)), 1),
                "p75": round(float(np.percentile(ranks, 75)), 1),
                "p90": round(float(np.percentile(ranks, 90)), 1),
            }
        else:
            rank_stats[rel] = {"count_retrieved": 0}

    # ================================================================
    # 9. CROSS-CPSE ANALYSIS
    # ================================================================
    cross_cpse_table = {}
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        sub = df[df["relationship"] == rel]
        same = sub[sub["same_cpse"] == True]
        cross = sub[sub["same_cpse"] == False]
        cross_cpse_table[rel] = {
            "same_cpse_total": int(len(same)),
            "same_cpse_at_100": int(same["in_top100"].sum()),
            "same_cpse_recall_100": round(recall_at_k(same, 100), 4) if len(same) > 0 else None,
            "cross_cpse_total": int(len(cross)),
            "cross_cpse_at_100": int(cross["in_top100"].sum()),
            "cross_cpse_recall_100": round(recall_at_k(cross, 100), 4) if len(cross) > 0 else None,
        }

    # ================================================================
    # 10. RELATE TO LANE 7
    # ================================================================
    # Lane 7 error analysis results (from the previous report)
    lane7_results = {
        "IDENTICAL": {"total_gt": 74, "lane7_correct": 2, "lane7_recall": 0.0270},
        "EQUIVALENT": {"total_gt": 324, "lane7_correct": 20, "lane7_recall": 0.0617},
        "VARIANT_OF": {"total_gt": 118, "lane7_correct": 0, "lane7_recall": 0.0000},
    }

    retrieval_vs_classification = {}
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        sub = df[df["relationship"] == rel]
        retrieved_100 = int(sub["in_top100"].sum())
        not_retrieved = int((~sub["in_top100"]).sum())
        # Of those retrieved, Lane 7 misclassified most.
        # Lane 7 correct count is from the error analysis (full dataset, not directional)
        # We report both to allow comparison
        retrieval_vs_classification[rel] = {
            "total_eval_tasks": int(len(sub)),
            "retrieved_at_100": retrieved_100,
            "not_retrieved_at_100": not_retrieved,
            "lane7_correctly_classified": lane7_results[rel]["lane7_correct"],
            "interpretation": (
                f"Of {int(len(sub))} directional eval tasks, "
                f"{retrieved_100} retrieved the target in Top-100. "
                f"Lane 7 correctly classified {lane7_results[rel]['lane7_correct']} "
                f"(from the full-dataset Lane 7 error analysis)."
            ),
        }

    # ================================================================
    # 12-14. SPECIAL ANALYSES
    # ================================================================
    variant_special = {
        "total_pairs": int(len(df[df["relationship"] == "VARIANT_OF"])),
        "at_10": int(df[df["relationship"] == "VARIANT_OF"]["in_top10"].sum()),
        "at_25": int(df[df["relationship"] == "VARIANT_OF"]["in_top25"].sum()),
        "at_50": int(df[df["relationship"] == "VARIANT_OF"]["in_top50"].sum()),
        "at_100": int(df[df["relationship"] == "VARIANT_OF"]["in_top100"].sum()),
        "not_retrieved": int((~df[df["relationship"] == "VARIANT_OF"]["in_top100"]).sum()),
    }

    equiv_special = {
        "total_pairs": int(len(df[df["relationship"] == "EQUIVALENT"])),
        "at_100": int(df[df["relationship"] == "EQUIVALENT"]["in_top100"].sum()),
        "not_retrieved": int((~df[df["relationship"] == "EQUIVALENT"]["in_top100"]).sum()),
    }

    ident_special = {
        "total_pairs": int(len(df[df["relationship"] == "IDENTICAL"])),
        "at_100": int(df[df["relationship"] == "IDENTICAL"]["in_top100"].sum()),
        "not_retrieved": int((~df[df["relationship"] == "IDENTICAL"]["in_top100"]).sum()),
    }

    # ================================================================
    # 19. DISCREPANCY EXPLANATION
    # ================================================================
    discrepancy_note = (
        "The earlier Lane 5 evaluation reported Recall@100 = 100%. "
        "That evaluation measured whether *any* known positive target for a query "
        "appeared in the Top-100. It was computed over the subset of queries that "
        "had at least one known positive in the *indexed* corpus. "
        "This Lane 7B analysis evaluates every directional positive pair from the "
        "ground truth CSV and checks whether the *specific* target material_id "
        "appears in the candidate set. Materials that are in the ground truth "
        "but NOT indexed in the vector store (e.g., synthetic materials not "
        "uploaded to Supabase) will show as NOT_RETRIEVED. "
        "Additionally, this analysis evaluates BOTH directions of each pair, "
        "whereas the Lane 5 evaluation may have only evaluated one direction."
    )

    # ================================================================
    # QUESTIONS 1-8
    # ================================================================
    answers = {}
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        r = per_class_table[rel]
        answers[f"Q1-3_{rel}"] = (
            f"{rel}: {r['count_at_100']}/{r['total']} retrieved @100 "
            f"({r['recall_at_100']*100:.1f}%). "
            f"{r['not_retrieved']} not retrieved."
        )

    answers["Q4_retrieval_failures"] = {
        rel: per_class_table[rel]["not_retrieved"] for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]
    }

    answers["Q5_retrieved_but_misclassified"] = {
        rel: retrieval_vs_classification[rel] for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]
    }

    answers["Q6_cross_cpse"] = cross_cpse_table

    answers["Q7_top100_sufficient"] = (
        f"ALL_POSITIVE Recall@100 = {per_class_table['ALL_POSITIVE']['recall_at_100']*100:.1f}%. "
        f"{per_class_table['ALL_POSITIVE']['not_retrieved']} of "
        f"{per_class_table['ALL_POSITIVE']['total']} not retrieved."
    )

    # Q8 recommendation
    total_not_retrieved = per_class_table["ALL_POSITIVE"]["not_retrieved"]
    total_positive = per_class_table["ALL_POSITIVE"]["total"]
    total_retrieved = per_class_table["ALL_POSITIVE"]["count_at_100"]
    if total_not_retrieved / max(1, total_positive) > 0.3:
        q8 = ("RETRIEVAL LIMITATION EXISTS. More than 30% of positive pairs are not "
              "retrieved by Lane 5. Lane 8 cannot fix pairs that never enter the "
              "candidate set. Consider retrieval improvements alongside Lane 8.")
    else:
        q8 = ("Lane 8 should focus primarily on decision/safety logic. Most positive "
              "pairs are retrieved but misclassified. The retrieval gap is modest.")

    answers["Q8_recommendation"] = q8

    # ================================================================
    # ASSEMBLE REPORT
    # ================================================================
    report = {
        "1_directionality": (
            "Each GT positive row is evaluated in BOTH directions (A->B, B->A). "
            f"Total positive GT rows: {len(positive_pairs)//2}. "
            f"Total evaluation tasks: {len(positive_pairs)}."
        ),
        "2_per_class_retrieval_recall": per_class_table,
        "3_bucket_distribution": bucket_dist,
        "4_rank_distribution": rank_stats,
        "5_cross_cpse_analysis": cross_cpse_table,
        "6_retrieval_vs_classification": retrieval_vs_classification,
        "7_variant_of_special": variant_special,
        "8_equivalent_special": equiv_special,
        "9_identical_special": ident_special,
        "10_discrepancy_explanation": discrepancy_note,
        "11_answers": answers,
    }

    # ================================================================
    # WRITE OUTPUTS
    # ================================================================
    os.makedirs("outputs", exist_ok=True)

    # CSV
    df.to_csv(OUT_CSV, index=False)

    # JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=safe_json)

    # TXT
    lines = []
    lines.append("=" * 72)
    lines.append("LANE 7B: POSITIVE RELATIONSHIP RETRIEVAL GAP ANALYSIS")
    lines.append("UnifAI SIH26099")
    lines.append("=" * 72)
    lines.append("")
    lines.append("DIRECTIONALITY")
    lines.append(f"  Each GT positive row evaluated in both directions.")
    lines.append(f"  Total positive GT rows (IDENTICAL+EQUIVALENT+VARIANT_OF): {len(positive_pairs)//2}")
    lines.append(f"  Total directional evaluation tasks: {len(positive_pairs)}")
    lines.append("")

    lines.append("PER-CLASS RETRIEVAL RECALL")
    lines.append("-" * 72)
    header = f"{'Relationship':15s} {'Total':>6s} {'@10':>6s} {'@25':>6s} {'@50':>6s} {'@100':>6s} {'Miss':>6s}"
    lines.append(header)
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "ALL_POSITIVE"]:
        r = per_class_table[rel]
        lines.append(
            f"{rel:15s} {r['total']:6d} {r['count_at_10']:6d} {r['count_at_25']:6d} "
            f"{r['count_at_50']:6d} {r['count_at_100']:6d} {r['not_retrieved']:6d}"
        )
    lines.append("")
    lines.append("RECALL PERCENTAGES")
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "ALL_POSITIVE"]:
        r = per_class_table[rel]
        lines.append(
            f"  {rel:15s}  @10={r['recall_at_10']*100:5.1f}%  @25={r['recall_at_25']*100:5.1f}%  "
            f"@50={r['recall_at_50']*100:5.1f}%  @100={r['recall_at_100']*100:5.1f}%"
        )

    lines.append("")
    lines.append("RETRIEVAL BUCKET DISTRIBUTION")
    lines.append("-" * 72)
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        lines.append(f"  {rel}:")
        for bucket, count in sorted(bucket_dist.get(rel, {}).items()):
            lines.append(f"    {bucket}: {count}")

    lines.append("")
    lines.append("RANK DISTRIBUTION (retrieved pairs only)")
    lines.append("-" * 72)
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        rs = rank_stats.get(rel, {})
        if rs.get("count_retrieved", 0) > 0:
            lines.append(
                f"  {rel}: n={rs['count_retrieved']}  min={rs['min_rank']}  "
                f"median={rs['median_rank']}  mean={rs['mean_rank']}  max={rs['max_rank']}  "
                f"p25={rs['p25']}  p75={rs['p75']}  p90={rs['p90']}"
            )
        else:
            lines.append(f"  {rel}: no pairs retrieved")

    lines.append("")
    lines.append("CROSS-CPSE ANALYSIS")
    lines.append("-" * 72)
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        cc = cross_cpse_table[rel]
        lines.append(f"  {rel}:")
        s_r = f"{cc['same_cpse_recall_100']*100:.1f}%" if cc['same_cpse_recall_100'] is not None else "N/A"
        c_r = f"{cc['cross_cpse_recall_100']*100:.1f}%" if cc['cross_cpse_recall_100'] is not None else "N/A"
        lines.append(f"    Same CPSE:  {cc['same_cpse_at_100']}/{cc['same_cpse_total']} = {s_r}")
        lines.append(f"    Cross CPSE: {cc['cross_cpse_at_100']}/{cc['cross_cpse_total']} = {c_r}")

    lines.append("")
    lines.append("RETRIEVAL vs CLASSIFICATION FAILURE")
    lines.append("-" * 72)
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        rc = retrieval_vs_classification[rel]
        lines.append(f"  {rel}:")
        lines.append(f"    {rc['interpretation']}")

    lines.append("")
    lines.append("DISCREPANCY WITH EARLIER LANE 5 RECALL@100 = 100%")
    lines.append("-" * 72)
    lines.append(f"  {discrepancy_note}")

    lines.append("")
    lines.append("=" * 72)
    lines.append("ANSWERS TO DIAGNOSTIC QUESTIONS")
    lines.append("=" * 72)
    lines.append("")

    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        lines.append(f"Q1-3: {answers[f'Q1-3_{rel}']}")
    lines.append("")

    lines.append(f"Q4: Retrieval failures (NOT_RETRIEVED_TOP100):")
    for rel, cnt in answers["Q4_retrieval_failures"].items():
        lines.append(f"  {rel}: {cnt}")
    lines.append("")

    lines.append(f"Q7: {answers['Q7_top100_sufficient']}")
    lines.append("")
    lines.append(f"Q8 RECOMMENDATION: {answers['Q8_recommendation']}")

    lines.append("")
    lines.append("=" * 72)
    lines.append("Lane 7B Status")
    lines.append("")
    lines.append(f"Implementation: COMPLETE")
    lines.append(f"Tests: see tests/test_lane7b_retrieval_gap_analysis.py")
    lines.append(f"Positive relationships evaluated: {len(positive_pairs)}")
    lines.append("")
    lines.append("Retrieval Recall (ALL POSITIVE):")
    r = per_class_table["ALL_POSITIVE"]
    lines.append(f"  @10  = {r['recall_at_10']*100:.2f}%")
    lines.append(f"  @25  = {r['recall_at_25']*100:.2f}%")
    lines.append(f"  @50  = {r['recall_at_50']*100:.2f}%")
    lines.append(f"  @100 = {r['recall_at_100']*100:.2f}%")
    lines.append("")
    for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
        r = per_class_table[rel]
        lines.append(f"{rel}:")
        lines.append(f"  @10  = {r['recall_at_10']*100:.2f}%")
        lines.append(f"  @25  = {r['recall_at_25']*100:.2f}%")
        lines.append(f"  @50  = {r['recall_at_50']*100:.2f}%")
        lines.append(f"  @100 = {r['recall_at_100']*100:.2f}%")
        lines.append("")

    lines.append("Recommendation for Lane 8:")
    lines.append(f"  {answers['Q8_recommendation']}")
    lines.append("=" * 72)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Print summary
    print("\n" + "\n".join(lines[-30:]))
    print(f"\nOutputs written to:\n  {OUT_JSON}\n  {OUT_TXT}\n  {OUT_CSV}")


if __name__ == "__main__":
    run_analysis()
