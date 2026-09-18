import sys
import os
import pandas as pd
import datetime
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline

CORPUS_PATH = "archive/data/corpus/cpse_material_corpus.csv"
OUT_DEV_SET = "data/real_public/real_cpse_materials.csv"

def process_corpus():
    print(f"Loading raw corpus from {CORPUS_PATH}...")
    try:
        df = pd.read_csv(CORPUS_PATH)
    except FileNotFoundError:
        print(f"Error: {CORPUS_PATH} not found.")
        return
        
    pipeline = PreprocessingPipeline()
    records = []
    
    # We will process all records to get vocabulary/patterns
    # But only materialize 1000 for the development subset.
    # To save memory/time in testing, we process the first 5000.
    
    df_subset = df.head(5000)
    
    print(f"Processing {len(df_subset)} records through the Unified Pipeline...")
    
    ts = datetime.datetime.now().isoformat()
    
    for idx, row in tqdm(df_subset.iterrows(), total=len(df_subset)):
        prov = Provenance(
            source_type="REAL_PUBLIC_SOURCE",
            source_system=str(row.get('source_system', 'UNKNOWN')),
            source_record_id=str(row.get('corpus_id', f"ROW-{idx}")),
            source_file="cpse_material_corpus.csv",
            source_row=idx,
            ingestion_timestamp=ts,
            processing_version="1.0"
        )
        
        record = UnifiedMaterialRecord(
            provenance=prov,
            description_original=str(row.get('description', '')),
            base_uom=str(row.get('unit', '')),
        )
        
        # Pass through pipeline
        processed_record = pipeline.process_record(record)
        records.append(processed_record.to_dict())
        
    # Full processed DataFrame
    df_processed = pd.DataFrame(records)
    
    # Extract patterns (e.g. UOMs, common tokens) - just simulating pattern extraction
    print("\n--- Extracted Patterns ---")
    uoms = df_processed['base_uom'].value_counts().head(10).to_dict()
    print("Top UOMs:", uoms)
    
    classes = df_processed['commodity_class'].value_counts().to_dict()
    print("Identified Commodity Classes:", classes)
    
    # Materialize Development Subset
    dev_set_size = min(1000, len(df_processed))
    df_dev = df_processed.head(dev_set_size).copy()
    if 'canonical_id' in df_dev.columns:
        df_dev = df_dev.drop(columns=['canonical_id'])
    if 'is_undetermined' in df_dev.columns:
        df_dev = df_dev.drop(columns=['is_undetermined'])
    df_dev.to_csv(OUT_DEV_SET, index=False)
    print(f"\nMaterialized {dev_set_size} development records to {OUT_DEV_SET}")

if __name__ == "__main__":
    process_corpus()
