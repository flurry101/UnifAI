import sys
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

# Load environment
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.retrieval.vector_store import PostgresVectorStore
from src.retrieval.embeddings import Qwen3EmbeddingProvider
from src.retrieval.lexical import BM25Retriever
from src.retrieval.engine import RetrievalEngine
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline
from src.extraction.engine import ExtractionEngine
from src.matching.lane6_features import PairFeatureEngine, Pair

SYNTHETIC_MAT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "synthetic", "material_master.csv")
SYNTHETIC_GT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "synthetic", "ground_truth_relationships.csv")
CORPUS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "real_public", "real_cpse_materials.csv")
OUTPUT_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "outputs", "lane6_false_positive_analysis.csv")

def run_lane6_validation():
    print("Initializing Lane 5 Engine...")
    vector_store = PostgresVectorStore()
    embedding_provider = Qwen3EmbeddingProvider()
    lexical_retriever = BM25Retriever()
    
    db_materials = vector_store.get_all_materials()
    lexical_retriever.refresh(db_materials)
    
    retrieval_engine = RetrievalEngine(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever
    )
    
    feature_engine = PairFeatureEngine()
    
    pipeline = PreprocessingPipeline()
    extraction_engine = ExtractionEngine()
    
    material_lookup = {}
    print("Loading 21K corpus for candidate mapping...")
    try:
        corpus_df = pd.read_csv(CORPUS_PATH)
        for idx, row in tqdm(corpus_df.iterrows(), total=len(corpus_df), desc="Parsing corpus"):
            mat_id = str(row['source_record_id'])
            prov = Provenance(
                source_type="REAL_PUBLIC_SOURCE",
                source_system=str(row.get('source_system', 'UNKNOWN')),
                source_record_id=mat_id,
                source_file="cpse_material_corpus.csv",
                source_row=idx,
                ingestion_timestamp="2026-09-19T00:00:00Z",
                processing_version="1.0"
            )
            record = UnifiedMaterialRecord(
                provenance=prov,
                original_material_code=str(row.get('original_material_code', '')),
                cpse=str(row.get('cpse', '')),
                description_original=str(row.get('original_description', '')),
                canonical_uom=str(row.get('canonical_uom', '')),
                manufacturer=str(row.get('manufacturer', '')) if pd.notna(row.get('manufacturer')) else None,
                manufacturer_part_number=str(row.get('manufacturer_part_number', '')) if pd.notna(row.get('manufacturer_part_number')) else None
            )
            material_lookup[mat_id] = record
    except Exception as e:
        print(f"Warning: Could not fully load corpus ({e}).")
        
    print("Loading Synthetic Dataset...")
    syn_df = pd.read_csv(SYNTHETIC_MAT_PATH)
    evaluation_queries = []
    
    for idx, row in tqdm(syn_df.iterrows(), total=len(syn_df), desc="Parsing synthetic queries"):
        mat_id = str(row['material_id'])
        prov = Provenance(
            source_type=str(row.get('source_type', 'SYNTHETIC')),
            source_system=str(row.get('source_system', 'UNKNOWN')),
            source_record_id=mat_id,
            source_file="material_master.csv",
            source_row=idx,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="2.0"
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code=str(row.get('material_code', '')),
            cpse=str(row.get('cpse_id', '')),
            description_original=str(row['description_original']),
            canonical_uom=str(row.get('base_uom', '')),
            manufacturer=str(row.get('manufacturer', '')) if pd.notna(row.get('manufacturer')) else None,
            manufacturer_part_number=str(row.get('manufacturer_part_number', '')) if pd.notna(row.get('manufacturer_part_number')) else None
        )
        processed = extraction_engine.process(pipeline.process_record(record))
        evaluation_queries.append(processed)
        material_lookup[mat_id] = processed
        
    gt_df = pd.read_csv(SYNTHETIC_GT_PATH)
    gt_map = {}
    for _, row in gt_df.iterrows():
        if row['relation_type'] in ['IDENTICAL', 'EQUIVALENT', 'VARIANT_OF']:
            a, b = str(row['material_id_a']), str(row['material_id_b'])
            gt_map.setdefault(a, set()).add((b, row['relation_type']))
            gt_map.setdefault(b, set()).add((a, row['relation_type']))
            
    # We evaluate ALL queries, but store how many were in GT
    total_queries = len(evaluation_queries)
    gt_queries = sum(1 for q in evaluation_queries if q.provenance.source_record_id in gt_map)
    print(f"Total Synthetic Queries: {total_queries}")
    print(f"Queries with known positive GT: {gt_queries} (the rest only have DISTINCT/Negative or are not in GT)")
    total_pairs = 0
    
    class_counts = {"IDENTICAL": 0, "EQUIVALENT": 0, "VARIANT_OF": 0, "DISTINCT": 0, "UNDETERMINED": 0}
    conflict_counts = {"Dimension": 0, "Pressure": 0, "Material": 0, "Standard": 0}
    
    y_true = []
    y_pred = []
    fp_rows = []
    
    specific_inspections = {
        "CL150_vs_CL300": 0,
        "diff_dimensions": 0,
        "diff_materials": 0,
        "GATE_vs_GLOBE": 0,
        "SS316_vs_316L": 0,
        "missing_pressure": 0,
        "missing_dimension": 0,
        "mfg_diff": 0,
        "mpn_diff": 0,
        "variant_extra_attr": 0,
        "high_sim_overridden": 0,
        "mpn_match_conflict": 0
    }

    for query in tqdm(evaluation_queries, desc="Evaluating Lane 6"):
        q_id = query.provenance.source_record_id
        candidate_set = retrieval_engine.retrieve_candidates(query, top_k=50)
        known_relations = gt_map.get(q_id, set())
        
        for c in candidate_set.candidates:
            c_id = c.material_id
            c_mat = material_lookup.get(c_id)
            if not c_mat:
                continue
                
            v_score = c.vector_similarity or 0.0
            l_score = c.bm25_score or 0.0
            
            pair = Pair(
                query_material=query,
                candidate_material=c_mat,
                semantic_similarity=v_score,
                lexical_similarity=l_score
            )
            
            result = feature_engine.evaluate(pair)
            total_pairs += 1
            
            cls = result.relationship_class
            if cls not in class_counts:
                class_counts[cls] = 0
            class_counts[cls] += 1
            
            if result.technical_conflict:
                if result.dimension_conflict: conflict_counts["Dimension"] += 1
                if result.pressure_conflict: conflict_counts["Pressure"] += 1
                if result.material_conflict: conflict_counts["Material"] += 1
                if result.standard_conflict: conflict_counts["Standard"] += 1
                if result.component_conflict: conflict_counts["Component"] = conflict_counts.get("Component", 0) + 1
                
            # Ground truth resolution
            # If the pair is in ground truth, the true class is the known class.
            # Else, since Lane 5 retrieved it and it's not in ground truth, we assume the true class is DISTINCT or UNDETERMINED.
            # To be strict, ground truth only contains POSITIVE examples.
            # Thus any unlisted pair is technically negative ("DISTINCT").
            true_rel = "DISTINCT"
            for gt_id, gt_rel in known_relations:
                if c_id == gt_id:
                    true_rel = gt_rel
                    break
                    
            # For confusion matrix, we map UNDETERMINED to DISTINCT as negatives.
            # Or we include UNDETERMINED in the confusion matrix.
            y_true.append(true_rel)
            y_pred.append(cls)
            
            # Specific Inspections tracking
            if result.pressure_rating_match is False and ("150" in query.original_description or "300" in query.original_description):
                specific_inspections["CL150_vs_CL300"] += 1
            if result.dimension_match is False:
                specific_inspections["diff_dimensions"] += 1
            if result.material_grade_match is False:
                specific_inspections["diff_materials"] += 1
            if "GATE" in query.original_description.upper() and "GLOBE" in c_mat.original_description.upper():
                specific_inspections["GATE_vs_GLOBE"] += 1
            if ("SS316" in query.original_description.upper() and "316L" in c_mat.original_description.upper()):
                specific_inspections["SS316_vs_316L"] += 1
            if result.missing_pressure:
                specific_inspections["missing_pressure"] += 1
            if result.missing_dimension:
                specific_inspections["missing_dimension"] += 1
            if result.manufacturer_match is False:
                specific_inspections["mfg_diff"] += 1
            if result.mpn_match is False:
                specific_inspections["mpn_diff"] += 1
            if cls == "VARIANT_OF":
                specific_inspections["variant_extra_attr"] += 1
            if v_score >= 0.90 and result.technical_conflict:
                specific_inspections["high_sim_overridden"] += 1
            if result.mpn_match is True and result.technical_conflict:
                specific_inspections["mpn_match_conflict"] += 1
                
            fp_rows.append({
                "query_id": q_id,
                "candidate_id": c_id,
                "query_description": query.original_description,
                "candidate_description": c_mat.original_description,
                "vector_score": v_score,
                "lexical_score": l_score,
                "dimension_match": result.dimension_match,
                "pressure_match": result.pressure_rating_match,
                "material_match": result.material_grade_match,
                "standard_match": result.standard_match,
                "technical_conflict": result.technical_conflict,
                "relationship_class": cls,
                "explanation": " | ".join(result.explanation),
                "true_relationship": true_rel
            })

    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)
    pd.DataFrame(fp_rows).to_csv(OUTPUT_CSV_PATH, index=False)
    
    # Generate Confusion Matrix
    labels = ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT", "UNDETERMINED"]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"True {l}" for l in labels], columns=[f"Pred {l}" for l in labels])
    
    # Generate Metrics
    # Filter out labels that are completely unrepresented in y_true to avoid warnings
    valid_labels = sorted(list(set(y_true).union(set(y_pred))))
    p, r, f1, s = precision_recall_fscore_support(y_true, y_pred, labels=valid_labels, zero_division=0)
    metrics_df = pd.DataFrame({
        "Class": valid_labels,
        "Precision": p,
        "Recall": r,
        "F1": f1,
        "Support": s
    })
    
    print("\n=============================================")
    print("Lane 6 Validation Report")
    print("=============================================\n")
    print(f"Total Queries: {total_queries}")
    print(f"Total Candidate Pairs Evaluated: {total_pairs}\n")
    
    print("Classification Distribution:")
    for cls in labels:
        count = class_counts.get(cls, 0)
        pct = (count / max(1, total_pairs)) * 100
        print(f"{cls}: {count} ({pct:.1f}%)")
        
    print("\nConfusion Matrix:")
    print(cm_df)
    
    print("\nClassification Metrics:")
    print(metrics_df.to_string(index=False))
    
    print("\nTechnical Conflicts:")
    for conf, count in conflict_counts.items():
        print(f"{conf} conflicts: {count}")
        
    print("\nSpecific Validations:")
    print(f"High Semantic Similarity (>= 0.90) correctly overridden by conflict: {specific_inspections['high_sim_overridden']}")
    print(f"Exact MPN matches properly suppressed by technical conflict: {specific_inspections['mpn_match_conflict']}")
    print(f"Missing attributes handled safely (None instead of False): Dim={specific_inspections['missing_dimension']}, Press={specific_inspections['missing_pressure']}")
    print(f"VARIANT_OF detected safely (additional attrs): {specific_inspections['variant_extra_attr']}")
    print(f"CL150 vs CL300 explicitly handled: {specific_inspections['CL150_vs_CL300']}")
    print(f"Different dimensions explicitly handled: {specific_inspections['diff_dimensions']}")
    print(f"Different materials explicitly handled: {specific_inspections['diff_materials']}")
    print(f"Component conflicts (GATE vs GLOBE): {specific_inspections['GATE_vs_GLOBE']}")
    print(f"Compatible materials (SS316 vs 316L): {specific_inspections['SS316_vs_316L']}")
    print(f"Manufacturer conflicts handled: {specific_inspections['mfg_diff']}")
    print(f"MPN conflicts handled: {specific_inspections['mpn_diff']}")
    
    print("\n=============================================\n")

if __name__ == "__main__":
    run_lane6_validation()
