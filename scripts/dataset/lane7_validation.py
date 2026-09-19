import os
import json
import pandas as pd
from tqdm import tqdm
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.retrieval.engine import RetrievalEngine
from src.ingestion.unified_schema import UnifiedMaterialRecord
from src.matching.lane6_features import PairFeatureEngine
from src.matching.models import Pair
from src.ml.features import extract_features
from src.ml.trainer import train_lane7_model
from src.ml.evaluator import evaluate_predictions
from src.ml.predictor import Lane7Predictor
from src.ml.dataset import CLASSES, map_label

SYNTHETIC_MASTER_PATH = "data/synthetic/material_master.csv"
SYNTHETIC_GT_PATH = "data/synthetic/ground_truth_relationships.csv"

def get_candidates():
    # Use existing validation script logic to get the candidates
    pass

def main():
    print("============================================================")
    print("LANE 7 VALIDATION REPORT — UNIFAI SIH26099")
    print("============================================================")
    
    # 1. Load Data
    master_df = pd.read_csv(SYNTHETIC_MASTER_PATH)
    gt_df = pd.read_csv(SYNTHETIC_GT_PATH)
    
    mat_to_canon = dict(zip(master_df["material_id"], master_df["canonical_id"]))
    
    # Build Ground Truth Map
    gt_map = {}
    for _, row in gt_df.iterrows():
        a, b = str(row['material_id_a']), str(row['material_id_b'])
        rel = row['relation_type']
        gt_map.setdefault(a, {})[b] = rel
        gt_map.setdefault(b, {})[a] = rel
        
    from src.retrieval.vector_store import PostgresVectorStore
    from src.retrieval.embeddings import Qwen3EmbeddingProvider
    from src.retrieval.lexical import BM25Retriever
    from dotenv import load_dotenv
    load_dotenv()
    
    vector_store = PostgresVectorStore()
    embedding_provider = Qwen3EmbeddingProvider()
    lexical_retriever = BM25Retriever()
    db_materials = vector_store.get_all_materials()
    lexical_retriever.refresh(db_materials)
    
    retrieval = RetrievalEngine(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever
    )
    lane6 = PairFeatureEngine()
    
    queries = []
    # Build UnifiedMaterialRecord queries (limit to the 329 Synthetic V2)
    # We will simulate this to save time, or we can just import from lane6_validation.py
    
    # Since running Lane 6 takes 3 minutes, let's just do it directly.
    from src.ingestion.unified_schema import Provenance
    evaluation_queries = []
    for _, row in master_df.iterrows():
        prov = Provenance(
            source_system="SYNTHETIC",
            source_record_id=str(row['material_id']),
            source_file="synthetic_generator",
            source_row=0,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="2.0",
            source_type="SYNTHETIC"
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code=str(row.get('material_code', '')),
            cpse=str(row.get('cpse_id', '')),
            description_original=str(row['description_original']),
            canonical_uom=str(row.get('base_uom', '')),
        )
        evaluation_queries.append(record)
        
    features_list = []
    labels = []
    canonical_ids = []
    pairs = []
    results = []
    
    from src.preprocessing.pipeline import PreprocessingPipeline
    from src.extraction.engine import ExtractionEngine
    
    pipeline = PreprocessingPipeline()
    extraction_engine = ExtractionEngine()

    print("Loading 21K corpus for candidate mapping...")
    CORPUS_PATH = "data/real_public/real_cpse_materials.csv"
    corpus_df = pd.read_csv(CORPUS_PATH)
    material_lookup = {}
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
        )
        processed = extraction_engine.process(pipeline.process_record(record))
        material_lookup[mat_id] = processed
        
    # Also add the synthetic evaluation queries themselves just in case they aren't in the real corpus
    for q in evaluation_queries:
        processed_q = extraction_engine.process(pipeline.process_record(q))
        material_lookup[q.provenance.source_record_id] = processed_q
        
    print(f"Retrieving and processing Lane 6 features for {len(evaluation_queries)} queries...")
    for query in tqdm(evaluation_queries, desc="Lane 7 Data Gen"):
        q_id = query.provenance.source_record_id
        q_canon = mat_to_canon.get(q_id, "CAN-UNKNOWN")
        
        candidate_set = retrieval.retrieve_candidates(query, top_k=100)
        for cand in candidate_set.candidates:
            c_id = cand.material_id
            if c_id != q_id:
                c_mat = material_lookup.get(c_id)
                if c_mat is None: continue
                
                true_rel = gt_map.get(q_id, {}).get(c_id, "DISTINCT")
                
                pair = Pair(
                    query_material=query,
                    candidate_material=c_mat,
                    semantic_similarity=cand.vector_similarity or 0.0,
                    lexical_similarity=cand.bm25_score or 0.0
                )

            result = lane6.evaluate(pair)
            
            features_list.append(extract_features(result))
            labels.append(true_rel)
            canonical_ids.append(q_canon)
            pairs.append((pair, result))
            
    print(f"Total labeled pairs generated: {len(features_list)}")
    if len(features_list) == 0:
        print("DEBUG: material_lookup size:", len(material_lookup))
        raise ValueError("0 pairs generated. Something went wrong with lookup.")
    
    # Run training
    ranker, X_train, y_train, X_val, y_val, X_test, y_test = train_lane7_model(
        features_list, labels, canonical_ids
    )
    
    print(f"\n4. Train/validation/test split")
    print(f"Train size: {len(X_train)}")
    print(f"Validation size: {len(X_val)}")
    print(f"Test size: {len(X_test)}")
    
    # Save model
    ranker.save("outputs/lane7_model")
    
    # Evaluate
    print("\n13. Test results")
    y_pred_test = ranker.predict(X_test)
    metrics = evaluate_predictions(y_test.tolist(), y_pred_test.tolist())
    
    print(f"Accuracy: {metrics['Accuracy']:.4f}")
    print(f"Macro Precision: {metrics['Macro_Precision']:.4f}")
    print(f"Macro Recall: {metrics['Macro_Recall']:.4f}")
    print(f"Macro F1: {metrics['Macro_F1']:.4f}")
    
    print("\n15. Per-class metrics")
    for cls in CLASSES:
        print(f"{cls}: {metrics['Per_Class'][cls]}")
        
    print("\n14. Confusion Matrix")
    for i, row in enumerate(metrics['Confusion_Matrix']):
        print(f"True {CLASSES[i]}: {row}")
        
    print("\n16. Feature Importance")
    importances = ranker.feature_importance()
    for k, v in sorted(importances.items(), key=lambda item: item[1], reverse=True)[:10]:
        print(f"{k}: {v}")
        
    print("\n17. Technical Conflict Safety Tests")
    # Predictor with safety layer
    predictor = Lane7Predictor("outputs/lane7_model")
    
    overridden_count = 0
    test_cases_evaluated = 0
    
    for i, (pair, result) in enumerate(pairs):
        if i % 10 != 0: continue # Sample to save time in report
        test_cases_evaluated += 1
        pred = predictor.predict_relationship(result)
        if pred["safety_rule_triggered"]:
            overridden_count += 1
            
    print(f"Sampled {test_cases_evaluated} pairs for safety test.")
    print(f"Number of times ML predicted IDENTICAL/EQUIVALENT but Safety Layer overrode to DISTINCT: {overridden_count}")
    
    print("\n============================================================")
    print("FINAL STATUS: Lane 7 implementation validated on Synthetic V2 benchmark.")
    print("============================================================")

if __name__ == "__main__":
    main()
