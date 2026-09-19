import sys
import os
import argparse
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.retrieval.vector_store import PostgresVectorStore
from src.retrieval.embeddings import Qwen3EmbeddingProvider
from src.retrieval.indexing import IndexingPipeline
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline
from src.extraction.engine import ExtractionEngine

CORPUS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "archive", "data", "corpus", "cpse_material_corpus.csv")

def get_21k_data() -> list[UnifiedMaterialRecord]:
    if not os.path.exists(CORPUS_PATH):
        raise FileNotFoundError(f"{CORPUS_PATH} not found.")
        
    df = pd.read_csv(CORPUS_PATH)
    pipeline = PreprocessingPipeline()
    engine = ExtractionEngine()
    
    records = []
    print(f"Loading and processing {len(df)} records from 21K corpus (this may take a moment)...")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Extracting Attributes"):
        prov = Provenance(
            source_type="REAL_PUBLIC_SOURCE",
            source_system=str(row.get('source_system', 'UNKNOWN')),
            source_record_id=str(row.get('corpus_id', f"ROW-{idx}")),
            source_file="cpse_material_corpus.csv",
            source_row=idx,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="1.0"
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code=str(row.get('corpus_id', f"ROW-{idx}")),
            cpse=str(row.get('source_system', 'UNKNOWN')),
            description_original=str(row.get('description', '')),
            canonical_uom=str(row.get('unit', '')),
        )
        processed_record = pipeline.process_record(record)
        processed_record = engine.process(processed_record)
        records.append(processed_record)
        
    return records

def main():
    print("Initializing Lane 5 Indexing Pipeline...")
    vector_store = PostgresVectorStore()
    embedding_provider = Qwen3EmbeddingProvider()
    pipeline = IndexingPipeline(vector_store, embedding_provider)
    
    records = get_21k_data()
    
    batch_size = 64
    print(f"Indexing {len(records)} records into Supabase in batches of {batch_size}...")
    
    import time
    start_time = time.time()
    
    total_records = len(records)
    total_skipped = 0
    total_embedded = 0
    total_failed = 0
    
    for i in tqdm(range(0, len(records), batch_size), desc="Indexing Batches"):
        batch = records[i:i + batch_size]
        metrics = pipeline.index_records(batch)
        total_skipped += metrics["skipped"]
        total_embedded += metrics["embedded"]
        total_failed += metrics["failed"]
        
    duration = time.time() - start_time
    print(f"Indexing complete in {duration:.2f} seconds.")
    
    # Calculate DB rows
    db_records = vector_store.get_all_materials()
    db_rows = len(db_records)
    
    # Calculate duplicates
    unique_ids = set([m["material_id"] for m in db_records])
    duplicates = db_rows - len(unique_ids)
    
    # Calculate overlap
    print("\n--- Real 21K Operational Metrics ---")
    print(f"Source records:        {total_records}")
    print(f"Already indexed:       {total_skipped}")
    print(f"New/changed:           {total_embedded}")
    print(f"Embedded:              {total_embedded}")
    print(f"Skipped unchanged:     {total_skipped}")
    print(f"Failed:                {total_failed}")
    print(f"DB rows after run:     {db_rows}")
    print(f"Duplicate material_id: {duplicates}")
    print(f"Indexing duration:     {duration:.2f}s")
    
    if total_embedded > 0:
        avg_throughput = total_embedded / duration
        print(f"Average throughput:    {avg_throughput:.2f} records/s")
    
if __name__ == "__main__":
    main()
