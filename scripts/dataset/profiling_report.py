import os
import sys
import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline

CORPUS_PATH = "archive/data/corpus/cpse_material_corpus.csv"

def generate_profiling_report():
    print(f"Loading raw corpus from {CORPUS_PATH}...")
    try:
        df = pd.read_csv(CORPUS_PATH)
    except FileNotFoundError:
        print(f"Error: {CORPUS_PATH} not found.")
        return

    pipeline = PreprocessingPipeline()
    
    total_records = len(df)
    records_with_descriptions = 0
    records_without_descriptions = 0
    
    original_descriptions = set()
    normalized_descriptions = set()
    
    descriptions_changed = 0
    descriptions_unchanged = 0
    
    uom_frequencies = {}
    
    print(f"Profiling {total_records} records...")
    
    for idx, row in tqdm(df.iterrows(), total=total_records):
        orig_desc = str(row.get('description', '')).strip()
        orig_uom = str(row.get('unit', '')).strip()
        
        if not orig_desc or orig_desc.lower() == 'nan':
            records_without_descriptions += 1
            continue
            
        records_with_descriptions += 1
        original_descriptions.add(orig_desc)
        
        # Normalize
        norm_desc = pipeline.normalize_text(orig_desc)
        normalized_descriptions.add(norm_desc)
        
        if orig_desc == norm_desc:
            descriptions_unchanged += 1
        else:
            descriptions_changed += 1
            
        # UOM
        if orig_uom and orig_uom.lower() != 'nan':
            norm_uom = pipeline.normalize_uom(orig_uom)
            uom_frequencies[norm_uom] = uom_frequencies.get(norm_uom, 0) + 1
            
    print("\n" + "="*50)
    print("PROFILING REPORT: LANE 2 (NORMALIZATION)")
    print("="*50)
    print(f"Total records:                  {total_records}")
    print(f"Records with descriptions:      {records_with_descriptions}")
    print(f"Records without descriptions:   {records_without_descriptions}")
    print(f"Unique original descriptions:   {len(original_descriptions)}")
    print(f"Unique normalized descriptions: {len(normalized_descriptions)}")
    
    compression = 0
    if len(original_descriptions) > 0:
        compression = (1 - (len(normalized_descriptions) / len(original_descriptions))) * 100
    print(f"Normalization compression:      {compression:.2f}%")
    
    print(f"Descriptions changed:           {descriptions_changed}")
    print(f"Descriptions unchanged:         {descriptions_unchanged}")
    
    change_rate = 0
    if records_with_descriptions > 0:
        change_rate = (descriptions_changed / records_with_descriptions) * 100
    print(f"Normalization change rate:      {change_rate:.2f}%")
    
    print("\n--- Top UOM Frequencies ---")
    sorted_uoms = sorted(uom_frequencies.items(), key=lambda x: x[1], reverse=True)
    for uom, count in sorted_uoms[:10]:
        print(f"  {uom}: {count}")
        
    print("\n--- Example Transformations ---")
    count = 0
    for idx, row in df.iterrows():
        orig_desc = str(row.get('description', '')).strip()
        if not orig_desc or orig_desc.lower() == 'nan': continue
        norm_desc = pipeline.normalize_text(orig_desc)
        if orig_desc != norm_desc:
            print(f"Original:   {orig_desc}")
            print(f"Normalized: {norm_desc}")
            print("-" * 30)
            count += 1
        if count >= 3:
            break

if __name__ == "__main__":
    generate_profiling_report()
