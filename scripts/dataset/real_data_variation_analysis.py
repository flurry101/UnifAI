"""
Real CPSE Variation & Pair-Mining Analysis — UnifAI SIH26099

READ-ONLY analysis. Does NOT modify any Lane 5/6/7/8 production logic.

Phases:
  1. Real data profiling
  2. Stratified query sampling (500-800 records)
  3. Candidate retrieval (existing Lane 5)
  4. Pool mining (A-H)
  5. Pair cleaning
  6. Human review queue
  7. Statistics report

Outputs:
  outputs/real_data_variation_analysis.json
  outputs/real_data_variation_analysis.txt
  outputs/real_data_variation_summary.csv
  outputs/real_pair_mining_report.json
  outputs/real_pair_mining_report.txt
  data/real_benchmark/real_candidate_pairs.csv
  data/real_benchmark/real_review_queue.csv
  data/real_benchmark/README.md
"""

import os, sys, json, math, re, hashlib
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
from src.matching.models import Pair
from src.ml.features import extract_features
from dotenv import load_dotenv

load_dotenv()

CORPUS_PATH = "archive/data/corpus/cpse_material_corpus.csv"
REAL_PUBLIC  = "data/real_public/real_cpse_materials.csv"
RANDOM_STATE = 42
QUERY_SAMPLE_SIZE = 700  # Target 500-800
TOP_K = 50

# Pool thresholds
SIM_HIGH = 0.85
SIM_MEDIUM = 0.70
LEX_HIGH = 60.0

# Common abbreviation patterns in CPSE materials
ABBREVIATION_PATTERNS = [
    (r'\bC\.?S\.?\b', 'CARBON STEEL'),
    (r'\bSS\s*316\b', 'STAINLESS STEEL 316'),
    (r'\bSS\s*304\b', 'STAINLESS STEEL 304'),
    (r'\bMS\b', 'MILD STEEL'),
    (r'\bGI\b', 'GALVANIZED IRON'),
    (r'\bCI\b', 'CAST IRON'),
    (r'\bHDPE\b', 'HIGH DENSITY POLYETHYLENE'),
    (r'\bPVC\b', 'POLYVINYL CHLORIDE'),
    (r'\bERW\b', 'ELECTRIC RESISTANCE WELDED'),
    (r'\bSMLs?\b', 'SEAMLESS'),
    (r'\bBW\b', 'BUTT WELD'),
    (r'\bSW\b', 'SOCKET WELD'),
    (r'\bRF\b', 'RAISED FACE'),
    (r'\bFF\b', 'FLAT FACE'),
    (r'\bNB\b', 'NOMINAL BORE'),
    (r'\bDN\b', 'DIAMETER NOMINAL'),
    (r'\bMOC\b', 'MATERIAL OF CONSTRUCTION'),
    (r'\bASME\b', 'AMERICAN SOCIETY OF MECHANICAL ENGINEERS'),
    (r'\bASTM\b', 'AMERICAN SOCIETY FOR TESTING AND MATERIALS'),
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
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    return obj


def count_abbreviations(text):
    """Count how many known abbreviation patterns appear in text."""
    if not text:
        return 0
    text_upper = text.upper()
    count = 0
    for pattern, _ in ABBREVIATION_PATTERNS:
        if re.search(pattern, text_upper):
            count += 1
    return count


def make_fingerprint(desc):
    """Simple fingerprint from description for duplicate detection."""
    if not desc:
        return None
    # Normalize: upper, remove punctuation, sort tokens
    text = re.sub(r'[^A-Z0-9\s]', '', desc.upper())
    tokens = sorted(text.split())
    return hashlib.md5(' '.join(tokens).encode()).hexdigest()[:16]


def make_pair_key(a, b):
    """Canonical pair key to avoid directional duplicates."""
    return tuple(sorted([str(a), str(b)]))


# ---------------------------------------------------------------
# PHASE 1: REAL DATA PROFILING
# ---------------------------------------------------------------
def phase1_profiling(corpus_df):
    """Profile the complete real corpus."""
    print("=" * 60)
    print("PHASE 1: Real Data Profiling")
    print("=" * 60)

    total = len(corpus_df)
    orgs = dict(corpus_df['organization'].value_counts())
    systems = dict(corpus_df['source_system'].value_counts())

    # Description analysis
    corpus_df['desc_len'] = corpus_df['description'].fillna('').str.len()
    corpus_df['desc_upper'] = corpus_df['description'].fillna('').str.upper().str.strip()
    unique_descs = corpus_df['desc_upper'].nunique()

    # Fingerprints
    corpus_df['fingerprint'] = corpus_df['description'].apply(make_fingerprint)
    unique_fps = corpus_df['fingerprint'].nunique()
    fp_counts = corpus_df['fingerprint'].value_counts()
    fp_dups = fp_counts[fp_counts > 1]

    # Fingerprint groups across CPSEs
    fp_cpse_groups = corpus_df.groupby('fingerprint')['organization'].nunique()
    cross_cpse_fps = int((fp_cpse_groups > 1).sum())

    # Abbreviation analysis
    corpus_df['abbrev_count'] = corpus_df['description'].apply(count_abbreviations)

    # Attribute extraction from descriptions
    from src.matching.attribute_extractors import (
        extract_dimension, extract_pressure, extract_material_grade, extract_standard
    )

    dims = corpus_df['description'].fillna('').apply(extract_dimension)
    press = corpus_df['description'].fillna('').apply(extract_pressure)
    mats = corpus_df['description'].fillna('').apply(extract_material_grade)
    stds = corpus_df['description'].fillna('').apply(extract_standard)

    # Component detection
    def detect_component(desc):
        d = str(desc).upper()
        components = ["GATE VALVE", "GLOBE VALVE", "BALL VALVE", "CHECK VALVE",
                       "BUTTERFLY VALVE", "PIPE", "FLANGE", "FITTING", "PUMP",
                       "MOTOR", "ACTUATOR", "GASKET", "BOLT", "NUT", "STUD"]
        for c in components:
            if c in d:
                return c
        return None

    comps = corpus_df['description'].apply(detect_component)

    profile = {
        "total_records": total,
        "organizations": orgs,
        "source_systems": systems,
        "unique_original_descriptions": unique_descs,
        "unique_fingerprints": unique_fps,
        "fingerprint_duplicate_groups": int(len(fp_dups)),
        "fingerprint_duplicate_records": int(fp_dups.sum()),
        "cross_cpse_fingerprints": cross_cpse_fps,
        "description_length": {
            "mean": round(float(corpus_df['desc_len'].mean()), 1),
            "median": round(float(corpus_df['desc_len'].median()), 1),
            "min": int(corpus_df['desc_len'].min()),
            "max": int(corpus_df['desc_len'].max()),
        },
        "abbreviation_frequency": {
            "records_with_abbreviations": int((corpus_df['abbrev_count'] > 0).sum()),
            "pct_with_abbreviations": round(100 * (corpus_df['abbrev_count'] > 0).mean(), 1),
            "mean_abbrev_per_record": round(float(corpus_df['abbrev_count'].mean()), 2),
        },
        "attribute_availability": {
            "dimension_extracted": int(dims.notna().sum()),
            "dimension_pct": round(100 * dims.notna().mean(), 1),
            "pressure_extracted": int(press.notna().sum()),
            "pressure_pct": round(100 * press.notna().mean(), 1),
            "material_grade_extracted": int(mats.notna().sum()),
            "material_grade_pct": round(100 * mats.notna().mean(), 1),
            "standard_extracted": int(stds.notna().sum()),
            "standard_pct": round(100 * stds.notna().mean(), 1),
            "component_detected": int(comps.notna().sum()),
            "component_pct": round(100 * comps.notna().mean(), 1),
        },
        "dimension_distribution": dict(dims.dropna().value_counts().head(15)),
        "pressure_distribution": dict(press.dropna().value_counts().head(15)),
        "material_grade_distribution": dict(mats.dropna().value_counts().head(15)),
        "component_distribution": dict(comps.dropna().value_counts().head(15)),
        "unit_distribution": dict(corpus_df['unit'].dropna().value_counts().head(10)),
    }

    # Save profiling outputs
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/real_data_variation_analysis.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, default=safe_json)

    # Summary CSV
    summary_rows = []
    for _, row in corpus_df.iterrows():
        summary_rows.append({
            "corpus_id": row["corpus_id"],
            "organization": row["organization"],
            "source_system": row["source_system"],
            "description": str(row["description"])[:200],
            "desc_len": row["desc_len"],
            "fingerprint": row["fingerprint"],
            "abbrev_count": row["abbrev_count"],
            "dimension": dims.iloc[_] if _ < len(dims) else None,
            "pressure": press.iloc[_] if _ < len(press) else None,
            "material_grade": mats.iloc[_] if _ < len(mats) else None,
            "component": comps.iloc[_] if _ < len(comps) else None,
        })
    pd.DataFrame(summary_rows).to_csv("outputs/real_data_variation_summary.csv", index=False)

    # TXT report
    lines = ["=" * 72, "REAL DATA VARIATION ANALYSIS", "UnifAI SIH26099", "=" * 72]
    lines.append(f"\nTotal records: {total}")
    lines.append(f"Organizations: {len(orgs)}")
    for org, cnt in orgs.items():
        lines.append(f"  {org}: {cnt}")
    lines.append(f"\nUnique descriptions: {unique_descs}")
    lines.append(f"Unique fingerprints: {unique_fps}")
    lines.append(f"Fingerprint duplicate groups: {len(fp_dups)}")
    lines.append(f"Cross-CPSE fingerprints: {cross_cpse_fps}")
    lines.append(f"\nAttribute availability:")
    for k, v in profile["attribute_availability"].items():
        lines.append(f"  {k}: {v}")
    lines.append(f"\nAbbreviation frequency:")
    for k, v in profile["abbreviation_frequency"].items():
        lines.append(f"  {k}: {v}")

    with open("outputs/real_data_variation_analysis.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  Total records: {total}")
    print(f"  Unique descriptions: {unique_descs}")
    print(f"  Fingerprint duplicates: {len(fp_dups)}")
    print(f"  Abbreviations in {profile['abbreviation_frequency']['pct_with_abbreviations']}% of records")

    return profile, corpus_df


# ---------------------------------------------------------------
# PHASE 2: STRATIFIED QUERY SAMPLING
# ---------------------------------------------------------------
def phase2_sampling(corpus_df):
    """Create a stratified sample of ~700 queries."""
    print("\n" + "=" * 60)
    print("PHASE 2: Stratified Query Sampling")
    print("=" * 60)

    rng = np.random.RandomState(RANDOM_STATE)

    # Filter to records with meaningful descriptions (> 10 chars)
    valid = corpus_df[corpus_df['desc_len'] > 10].copy()
    print(f"  Valid records (desc > 10 chars): {len(valid)}")

    sampled_indices = set()
    strata_report = {}

    # Stratum 1: Per-organization proportional
    for org, org_df in valid.groupby('organization'):
        n = max(10, int(QUERY_SAMPLE_SIZE * len(org_df) / len(valid)))
        n = min(n, len(org_df))
        idx = rng.choice(org_df.index, size=n, replace=False)
        sampled_indices.update(idx)
        strata_report[f"org_{org[:20]}"] = int(n)

    # Stratum 2: Records with rich attributes (dim+press or dim+mat)
    from src.matching.attribute_extractors import extract_dimension, extract_pressure, extract_material_grade
    rich = valid[
        valid['description'].apply(lambda x: extract_dimension(str(x)) is not None) &
        (valid['description'].apply(lambda x: extract_pressure(str(x)) is not None) |
         valid['description'].apply(lambda x: extract_material_grade(str(x)) is not None))
    ]
    n_rich = min(100, len(rich))
    if n_rich > 0:
        idx = rng.choice(rich.index, size=n_rich, replace=False)
        sampled_indices.update(idx)
    strata_report["rich_attributes"] = int(n_rich)

    # Stratum 3: Records with abbreviations
    abbrev = valid[valid['abbrev_count'] >= 2]
    n_abbrev = min(80, len(abbrev))
    if n_abbrev > 0:
        idx = rng.choice(abbrev.index, size=n_abbrev, replace=False)
        sampled_indices.update(idx)
    strata_report["high_abbreviations"] = int(n_abbrev)

    # Stratum 4: Short descriptions (sparse info)
    short = valid[(valid['desc_len'] >= 11) & (valid['desc_len'] <= 30)]
    n_short = min(50, len(short))
    if n_short > 0:
        idx = rng.choice(short.index, size=n_short, replace=False)
        sampled_indices.update(idx)
    strata_report["short_descriptions"] = int(n_short)

    # Stratum 5: Long descriptions (rich info)
    long_desc = valid[valid['desc_len'] >= 150]
    n_long = min(50, len(long_desc))
    if n_long > 0:
        idx = rng.choice(long_desc.index, size=n_long, replace=False)
        sampled_indices.update(idx)
    strata_report["long_descriptions"] = int(n_long)

    # Stratum 6: Fingerprint duplicates (likely similar materials)
    fp_counts = valid['fingerprint'].value_counts()
    dup_fps = set(fp_counts[fp_counts > 1].index)
    fp_dups = valid[valid['fingerprint'].isin(dup_fps)]
    n_fp = min(80, len(fp_dups))
    if n_fp > 0:
        idx = rng.choice(fp_dups.index, size=n_fp, replace=False)
        sampled_indices.update(idx)
    strata_report["fingerprint_duplicates"] = int(n_fp)

    sample_df = valid.loc[list(sampled_indices)]

    print(f"  Sampled queries: {len(sample_df)}")
    for k, v in strata_report.items():
        print(f"    {k}: {v}")

    return sample_df, strata_report


# ---------------------------------------------------------------
# PHASE 3: CANDIDATE RETRIEVAL + LANE 6
# ---------------------------------------------------------------
def phase3_retrieval(sample_df, corpus_df):
    """Retrieve candidates for sampled queries using existing Lane 5."""
    print("\n" + "=" * 60)
    print("PHASE 3: Candidate Retrieval + Lane 6 Features")
    print("=" * 60)

    vector_store = PostgresVectorStore()
    embedding_provider = Qwen3EmbeddingProvider()
    lexical_retriever = BM25Retriever()
    db_materials = vector_store.get_all_materials()
    lexical_retriever.refresh(db_materials)

    retrieval = RetrievalEngine(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever,
    )
    lane6 = PairFeatureEngine()
    pipeline = PreprocessingPipeline()
    ext_eng = ExtractionEngine()

    # Build material lookup from the FULL corpus (not the 1000-row subset)
    # Use the corpus_df (21K) directly + vector store text for retrieval representation
    print("  Building material lookup from full corpus...")

    # Build a lookup: material_id -> {org, desc, ...} from the 21K corpus
    corpus_lookup = {}
    for _, row in tqdm(corpus_df.iterrows(), total=len(corpus_df), desc="  Indexing corpus"):
        cid = str(row["corpus_id"])
        corpus_lookup[cid] = {
            "corpus_id": cid,
            "organization": str(row.get("organization", "")),
            "source_system": str(row.get("source_system", "")),
            "description": str(row.get("description", "")),
            "unit": str(row.get("unit", "")),
        }

    # Build UMR lookup for candidates (lazy: create on demand)
    def get_candidate_umr(c_id):
        info = corpus_lookup.get(c_id)
        if info is None:
            return None
        prov = Provenance(
            source_type="REAL_PUBLIC_SOURCE",
            source_system=info["source_system"],
            source_record_id=c_id,
            source_file="cpse_material_corpus.csv",
            source_row=0,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="1.0",
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code="",
            cpse=info["organization"],
            original_description=info["description"],
            canonical_uom=info["unit"],
        )
        return pipeline.process_record(record)

    # Build query records
    all_pairs = []
    seen_pair_keys = set()
    retrieval_errors = 0

    print(f"  Retrieving candidates for {len(sample_df)} queries (Top-K={TOP_K})...")
    for _, qrow in tqdm(sample_df.iterrows(), total=len(sample_df), desc="  Retrieval"):
        q_id = str(qrow["corpus_id"])
        q_org = str(qrow["organization"])
        q_desc = str(qrow["description"])

        # Build query UMR and PREPROCESS (critical: sets normalized_description)
        prov = Provenance(
            source_type="REAL_PUBLIC_SOURCE",
            source_system=str(qrow.get("source_system", "UNKNOWN")),
            source_record_id=q_id,
            source_file="cpse_material_corpus.csv",
            source_row=0,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="1.0",
        )
        query_record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code="",
            cpse=q_org,
            original_description=q_desc,
            canonical_uom=str(qrow.get("unit", "")),
        )
        # Preprocess to set normalized_description (required by RetrievalRepresentationBuilder)
        query_record = pipeline.process_record(query_record)

        try:
            candidate_set = retrieval.retrieve_candidates(query_record, top_k=TOP_K)
        except Exception as e:
            retrieval_errors += 1
            continue

        for cand in candidate_set.candidates:
            c_id = cand.material_id
            if c_id == q_id:
                continue

            pair_key = make_pair_key(q_id, c_id)
            if pair_key in seen_pair_keys:
                continue
            seen_pair_keys.add(pair_key)

            c_mat = get_candidate_umr(c_id)
            if c_mat is None:
                continue

            c_info = corpus_lookup.get(c_id, {})
            c_org = c_info.get("organization", "")
            c_desc = c_info.get("description", "")

            # Lane 6 features
            pair = Pair(
                query_material=query_record,
                candidate_material=c_mat,
                semantic_similarity=cand.vector_similarity or 0.0,
                lexical_similarity=cand.bm25_score or 0.0,
            )
            try:
                result = lane6.evaluate(pair)
                feats = extract_features(result)
            except Exception:
                continue

            # Abbreviation variation detection
            q_abbrev = count_abbreviations(q_desc)
            c_abbrev = count_abbreviations(c_desc)
            abbrev_diff = abs(q_abbrev - c_abbrev)

            q_fp = make_fingerprint(q_desc)
            c_fp = make_fingerprint(c_desc)
            fingerprint_match = (q_fp == c_fp) if (q_fp and c_fp) else False

            row = {
                "query_id": q_id,
                "candidate_id": c_id,
                "query_cpse": q_org,
                "candidate_cpse": c_org,
                "query_description": q_desc[:200],
                "candidate_description": c_desc[:200],
                "semantic_similarity": cand.vector_similarity or 0.0,
                "lexical_similarity": cand.bm25_score or 0.0,
                "retrieval_rank": cand.retrieval_rank,
                "retrieval_sources": ",".join(cand.retrieval_sources),
                "cross_cpse": (q_org != c_org and q_org != "" and c_org != ""),
                "fingerprint_match": fingerprint_match,
                "abbrev_diff": abbrev_diff,
                "q_abbrev_count": q_abbrev,
                "c_abbrev_count": c_abbrev,
                # Lane 6 features
                "technical_conflict": bool(result.technical_conflict),
                "dimension_match": safe_json(feats.get("dimension_match")),
                "pressure_rating_match": safe_json(feats.get("pressure_rating_match")),
                "material_grade_match": safe_json(feats.get("material_grade_match")),
                "standard_match": safe_json(feats.get("standard_match")),
                "component_type_match": safe_json(feats.get("component_type_match")),
                "manufacturer_match": safe_json(feats.get("manufacturer_match")),
                "mpn_match": safe_json(feats.get("mpn_match")),
                "uom_compatibility": safe_json(feats.get("uom_compatibility")),
                "missing_dimension": bool(feats.get("missing_dimension", 0)),
                "missing_pressure": bool(feats.get("missing_pressure", 0)),
                "missing_material": bool(feats.get("missing_material", 0)),
                "missing_standard": bool(feats.get("missing_standard", 0)),
                "missing_component": bool(feats.get("missing_component", 0)),
                "technical_attribute_overlap": int(feats.get("technical_attribute_overlap", 0)),
                "additional_attribute_count": int(feats.get("additional_attribute_count", 0)),
                "lane6_relationship": result.relationship_class,
                "lane6_explanation": "; ".join(result.explanation)[:200],
            }
            all_pairs.append(row)

    pairs_df = pd.DataFrame(all_pairs)
    print(f"  Total unique pairs: {len(pairs_df)}")
    return pairs_df


# ---------------------------------------------------------------
# PHASE 4: POOL MINING
# ---------------------------------------------------------------
def phase4_pool_mining(pairs_df):
    """Assign candidate pairs to pools A-H."""
    print("\n" + "=" * 60)
    print("PHASE 4: Pool Mining")
    print("=" * 60)

    pools = {p: set() for p in "ABCDEFGH"}

    for idx, row in pairs_df.iterrows():
        sim = row["semantic_similarity"]
        lex = row["lexical_similarity"]
        conflict = row["technical_conflict"]
        cross = row["cross_cpse"]
        fp_match = row["fingerprint_match"]
        missing_count = sum([
            row["missing_dimension"], row["missing_pressure"],
            row["missing_material"], row["missing_standard"],
            row["missing_component"]
        ])
        abbrev_d = row["abbrev_diff"]
        extra = row["additional_attribute_count"]

        # Pool A: High semantic similarity
        if sim >= SIM_HIGH:
            pools["A"].add(idx)

        # Pool B: High lexical similarity
        if lex >= LEX_HIGH:
            pools["B"].add(idx)

        # Pool C: High similarity + technical conflict
        if sim >= SIM_MEDIUM and conflict:
            pools["C"].add(idx)

        # Pool D: Cross-CPSE
        if cross and sim >= SIM_MEDIUM:
            pools["D"].add(idx)

        # Pool E: Same fingerprint / different description
        if fp_match:
            pools["E"].add(idx)

        # Pool F: Missing information (high sim but missing attrs)
        if sim >= SIM_MEDIUM and missing_count >= 3:
            pools["F"].add(idx)

        # Pool G: Possible variant (high sim, no conflict, extra info)
        if sim >= SIM_MEDIUM and not conflict and extra > 0:
            pools["G"].add(idx)

        # Pool H: Abbreviation/normalization variation
        if sim >= SIM_MEDIUM and abbrev_d >= 2:
            pools["H"].add(idx)

    # Assign pool labels to dataframe
    pool_labels = []
    for idx in pairs_df.index:
        assigned = [p for p in "ABCDEFGH" if idx in pools[p]]
        pool_labels.append(",".join(assigned) if assigned else "NONE")
    pairs_df["candidate_pool"] = pool_labels

    pool_counts = {p: len(s) for p, s in pools.items()}
    pool_names = {
        "A": "HIGH_SEMANTIC", "B": "HIGH_LEXICAL", "C": "HIGH_SIM+CONFLICT",
        "D": "CROSS_CPSE", "E": "SAME_FINGERPRINT", "F": "MISSING_INFO",
        "G": "POSSIBLE_VARIANT", "H": "ABBREV_VARIATION"
    }

    for p in "ABCDEFGH":
        print(f"  Pool {p} ({pool_names[p]}): {pool_counts[p]}")

    # Overlap
    all_pooled = set()
    for s in pools.values():
        all_pooled.update(s)
    multi_pool = sum(1 for idx in all_pooled
                     if sum(1 for p in pools.values() if idx in p) > 1)

    print(f"  Total unique pooled pairs: {len(all_pooled)}")
    print(f"  Pairs in multiple pools: {multi_pool}")

    return pairs_df, pools, pool_counts


# ---------------------------------------------------------------
# PHASE 5 & 6: REVIEW QUEUE
# ---------------------------------------------------------------
def phase5_6_review_queue(pairs_df, pools, pool_counts):
    """Create stratified human review queue."""
    print("\n" + "=" * 60)
    print("PHASE 5-6: Human Review Queue")
    print("=" * 60)

    rng = np.random.RandomState(RANDOM_STATE)
    TARGET_REVIEW = 800
    per_pool_target = TARGET_REVIEW // 8  # 100 per pool

    review_indices = set()

    for pool_name in "ABCDEFGH":
        pool_indices = list(pools[pool_name])
        if not pool_indices:
            continue
        n = min(per_pool_target, len(pool_indices))
        selected = rng.choice(pool_indices, size=n, replace=False)
        review_indices.update(selected)

    # If under target, fill from remaining pooled pairs
    all_pooled = set()
    for s in pools.values():
        all_pooled.update(s)
    remaining = list(all_pooled - review_indices)
    if len(review_indices) < TARGET_REVIEW and remaining:
        n_extra = min(TARGET_REVIEW - len(review_indices), len(remaining))
        extra = rng.choice(remaining, size=n_extra, replace=False)
        review_indices.update(extra)

    review_df = pairs_df.loc[list(review_indices)].copy()

    # Add human review columns
    review_df["review_relation"] = None  # NULL = not yet reviewed
    review_df["review_status"] = "UNREVIEWED"
    review_df["reviewer_notes"] = ""
    review_df["evidence_type"] = ""

    # Save
    os.makedirs("data/real_benchmark", exist_ok=True)
    pairs_df.to_csv("data/real_benchmark/real_candidate_pairs.csv", index=False)
    review_df.to_csv("data/real_benchmark/real_review_queue.csv", index=False)

    # README
    readme = f"""# Real CPSE Benchmark — UnifAI SIH26099

## Purpose
This directory contains candidate pairs mined from the real 21,513-record CPSE corpus
for human review and benchmark construction.

## Files
- `real_candidate_pairs.csv`: All mined candidate pairs with automated signals
- `real_review_queue.csv`: Stratified sample for human review

## Important
- `review_relation` is initially NULL (not reviewed)
- `review_status` is initially UNREVIEWED
- Automated signals (semantic_similarity, technical_conflict, etc.) are NOT labels
- Do NOT train on these signals as ground truth
- Human review must populate `review_relation` before use as training labels

## Review Schema
- review_relation: IDENTICAL | EQUIVALENT | VARIANT_OF | DISTINCT | UNDETERMINED
- review_status: UNREVIEWED | REVIEWED
- reviewer_notes: free text
- evidence_type: EXACT_ATTRIBUTE_MATCH | TECHNICAL_CONFLICT | MISSING_ATTRIBUTE | etc.

## Pool Definitions
- A: High semantic similarity (≥{SIM_HIGH})
- B: High lexical similarity (≥{LEX_HIGH})
- C: High similarity + technical conflict
- D: Cross-CPSE candidates
- E: Same fingerprint / different description
- F: High similarity + missing attributes
- G: Possible variant (high sim, no conflict, extra info)
- H: Abbreviation/normalization variation

## Statistics
- Total candidate pairs: {len(pairs_df)}
- Review queue size: {len(review_df)}
- Generated: 2026-09-19
- Random seed: {RANDOM_STATE}
"""
    with open("data/real_benchmark/README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"  Review queue: {len(review_df)} pairs")
    print(f"  Total candidate pairs: {len(pairs_df)}")

    return review_df


# ---------------------------------------------------------------
# PHASE 7-9: FINAL REPORT
# ---------------------------------------------------------------
def phase7_report(profile, strata_report, pairs_df, pools, pool_counts, review_df):
    """Generate final mining report."""
    print("\n" + "=" * 60)
    print("PHASE 7: Final Report")
    print("=" * 60)

    # Missingness in mined pairs
    miss_stats = {}
    for feat in ["missing_dimension", "missing_pressure", "missing_material",
                  "missing_standard", "missing_component"]:
        miss_stats[feat] = {
            "count": int(pairs_df[feat].sum()),
            "pct": round(100 * pairs_df[feat].mean(), 1),
        }

    # Technical conflict frequency
    conflict_count = int(pairs_df["technical_conflict"].sum())
    conflict_pct = round(100 * pairs_df["technical_conflict"].mean(), 1)

    # Cross-CPSE
    cross_count = int(pairs_df["cross_cpse"].sum())
    cross_pct = round(100 * pairs_df["cross_cpse"].mean(), 1)

    # Fingerprint match
    fp_count = int(pairs_df["fingerprint_match"].sum())

    # Overlap between pools
    pool_overlaps = {}
    for p1 in "ABCDEFGH":
        for p2 in "ABCDEFGH":
            if p1 >= p2:
                continue
            overlap = len(pools[p1] & pools[p2])
            if overlap > 0:
                pool_overlaps[f"{p1}_{p2}"] = overlap

    report = {
        "total_real_records": profile["total_records"],
        "sampled_query_count": sum(strata_report.values()),
        "strata_details": strata_report,
        "cpse_coverage": profile["organizations"],
        "total_candidate_pairs": len(pairs_df),
        "pool_counts": {
            "A_HIGH_SEMANTIC": pool_counts["A"],
            "B_HIGH_LEXICAL": pool_counts["B"],
            "C_HIGH_SIM_CONFLICT": pool_counts["C"],
            "D_CROSS_CPSE": pool_counts["D"],
            "E_SAME_FINGERPRINT": pool_counts["E"],
            "F_MISSING_INFO": pool_counts["F"],
            "G_POSSIBLE_VARIANT": pool_counts["G"],
            "H_ABBREV_VARIATION": pool_counts["H"],
        },
        "pool_overlaps": pool_overlaps,
        "review_queue_size": len(review_df),
        "missingness": miss_stats,
        "technical_conflict": {"count": conflict_count, "pct": conflict_pct},
        "cross_cpse": {"count": cross_count, "pct": cross_pct},
        "fingerprint_matches": fp_count,
        "attribute_availability": profile["attribute_availability"],
        "abbreviation_stats": profile["abbreviation_frequency"],
        "lanes_modified": "NONE — Lane 5/6/7/8 production logic unchanged",
    }

    with open("outputs/real_pair_mining_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=safe_json)

    # TXT
    lines = ["=" * 72, "REAL PAIR MINING REPORT", "UnifAI SIH26099", "=" * 72]
    lines.append(f"\nTotal real records: {report['total_real_records']}")
    lines.append(f"Sampled queries: {report['sampled_query_count']}")
    lines.append(f"Total candidate pairs: {report['total_candidate_pairs']}")
    lines.append(f"\nPOOL COUNTS")
    lines.append("-" * 40)
    for k, v in report["pool_counts"].items():
        lines.append(f"  {k:25s}: {v}")
    lines.append(f"\nReview queue: {report['review_queue_size']}")
    lines.append(f"\nTechnical conflicts: {conflict_count} ({conflict_pct}%)")
    lines.append(f"Cross-CPSE pairs: {cross_count} ({cross_pct}%)")
    lines.append(f"Fingerprint matches: {fp_count}")
    lines.append(f"\nMISSINGNESS IN MINED PAIRS")
    lines.append("-" * 40)
    for k, v in miss_stats.items():
        lines.append(f"  {k:25s}: {v['pct']}%")
    lines.append(f"\nATTRIBUTE AVAILABILITY IN CORPUS")
    lines.append("-" * 40)
    for k, v in profile["attribute_availability"].items():
        lines.append(f"  {k}: {v}")
    lines.append(f"\nPOOL OVERLAPS")
    lines.append("-" * 40)
    for k, v in sorted(pool_overlaps.items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")
    lines.append(f"\nLanes 5-8 production logic: UNCHANGED")
    lines.append("=" * 72)

    with open("outputs/real_pair_mining_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines[-20:]))


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def main():
    print("Loading real corpus...")
    corpus_df = pd.read_csv(CORPUS_PATH)
    print(f"Corpus loaded: {len(corpus_df)} records")

    # Phase 1
    profile, corpus_df = phase1_profiling(corpus_df)

    # Phase 2
    sample_df, strata_report = phase2_sampling(corpus_df)

    # Phase 3
    pairs_df = phase3_retrieval(sample_df, corpus_df)

    if len(pairs_df) == 0:
        print("ERROR: No pairs generated. Check retrieval.")
        return

    # Phase 4
    pairs_df, pools, pool_counts = phase4_pool_mining(pairs_df)

    # Phase 5-6
    review_df = phase5_6_review_queue(pairs_df, pools, pool_counts)

    # Phase 7
    phase7_report(profile, strata_report, pairs_df, pools, pool_counts, review_df)

    print("\nDone. All outputs saved.")
    print("Lane 5/6/7/8 production logic: UNCHANGED")


if __name__ == "__main__":
    main()
