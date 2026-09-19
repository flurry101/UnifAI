import os
import sys
import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline
from src.extraction.engine import ExtractionEngine
from src.fingerprint.builder import FingerprintBuilder

CORPUS_PATH = "archive/data/corpus/cpse_material_corpus.csv"

def run_synthetic_validation(pipeline, engine, builder):
    print("\n" + "="*50)
    print("SYNTHETIC CONTROLLED VALIDATION")
    print("="*50)
    
    def get_prov(cpse="CPSE_A", record_id="1"):
        return Provenance(
            source_type="SYNTHETIC", source_system="SYS", 
            source_record_id=record_id, source_file="f.csv", source_row=1, 
            ingestion_timestamp="now", processing_version="v3"
        )
        
    def get_fp(text, cpse="CPSE_A", record_id="1"):
        r = UnifiedMaterialRecord(provenance=get_prov(cpse, record_id), original_description=text)
        r = pipeline.process_record(r)
        r = engine.process(r)
        return builder.build(r)

    # 1. Same technical identity with different descriptions
    fp1 = get_fp("GATE VALVE, CS, 4 IN, CL150, RF, ASTM A216 WCB")
    fp2 = get_fp("GATE VALVE CARBON STEEL 4 IN CLASS 150 RF A216 WCB")
    print(f"1. Same technical identity with diff desc : {'PASS' if fp1.fingerprint_id == fp2.fingerprint_id else 'FAIL'}")
    
    # 2. Technical mutation: CL150 -> CL300
    fp3 = get_fp("GATE VALVE, CS, 4 IN, CL300, RF, ASTM A216 WCB")
    print(f"2. Technical mutation (CL150 vs CL300)      : {'PASS' if fp1.fingerprint_id != fp3.fingerprint_id else 'FAIL'}")
    
    # 3. Size mutation: 4 IN -> 6 IN
    fp4 = get_fp("GATE VALVE, CS, 6 IN, CL150, RF, ASTM A216 WCB")
    print(f"3. Size mutation (4 IN vs 6 IN)             : {'PASS' if fp1.fingerprint_id != fp4.fingerprint_id else 'FAIL'}")
    
    # 4. Grade mutation: WCB -> LCC
    fp5 = get_fp("GATE VALVE, CS, 4 IN, CL150, RF, ASTM A352 LCC")
    print(f"4. Grade mutation (WCB vs LCC)              : {'PASS' if fp1.fingerprint_id != fp5.fingerprint_id else 'FAIL'}")
    
    # 5. Missing attribute preserved deterministic
    fp_missing = get_fp("GATE VALVE, CS, 4 IN, RF")
    print(f"5. Missing attribute preserved correctly    : {'PASS' if 'pressure_class:null' in fp_missing.canonical_serialization else 'FAIL'}")
    
    # 6. Same material from different CPSEs -> Same fingerprint
    fp_ongc = get_fp("GATE VALVE, CS, 4 IN, CL150", cpse="ONGC", record_id="999")
    fp_ntpc = get_fp("GATE VALVE, CS, 4 IN, CL150", cpse="NTPC", record_id="888")
    print(f"6. Same technical identity, different CPSEs : {'PASS' if fp_ongc.fingerprint_id == fp_ntpc.fingerprint_id else 'FAIL'}")

def run_real_profiling(pipeline, engine, builder):
    print("\n" + "="*50)
    print("REAL DATA FINGERPRINT PROFILING (21K)")
    print("="*50)
    
    try:
        df = pd.read_csv(CORPUS_PATH)
    except FileNotFoundError:
        print(f"Error: {CORPUS_PATH} not found.")
        return
        
    total_records = len(df)
    status_counts = {"COMPLETE": 0, "PARTIAL": 0, "AMBIGUOUS": 0, "CONFLICTED": 0}
    unique_fingerprints = set()
    fingerprint_groups = {}
    
    print(f"Profiling {total_records} records...")
    
    for idx, row in tqdm(df.iterrows(), total=total_records):
        orig_desc = str(row.get('description', '')).strip()
        if not orig_desc or orig_desc.lower() == 'nan':
            continue
            
        prov = Provenance(
            source_type="REAL", source_system="SYS", source_record_id=str(idx),
            source_file="cpse_material_corpus.csv", source_row=idx,
            ingestion_timestamp="test", processing_version="v3"
        )
        
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_description=orig_desc,
            canonical_uom=str(row.get('unit', ''))
        )
        
        record = pipeline.process_record(record)
        record = engine.process(record)
        fp = builder.build(record)
        
        status_counts[fp.fingerprint_status] += 1
        unique_fingerprints.add(fp.fingerprint_id)
        
        if fp.fingerprint_id not in fingerprint_groups:
            fingerprint_groups[fp.fingerprint_id] = 0
        fingerprint_groups[fp.fingerprint_id] += 1
        
    duplicate_groups = sum(1 for v in fingerprint_groups.values() if v > 1)
    
    print("\nFINGERPRINT PROFILE")
    print(f"Total records processed:   {total_records}")
    print(f"Unique Fingerprints:       {len(unique_fingerprints)}")
    print(f"Duplicate FP Groups:       {duplicate_groups}")
    print("\nSTATUS COUNTS:")
    for status, count in status_counts.items():
        print(f"  {status.ljust(12)} : {count}")
    print("\nNote: Duplicate fingerprints indicate identical extracted technical representations under current schema.")

if __name__ == "__main__":
    pipeline = PreprocessingPipeline()
    engine = ExtractionEngine()
    builder = FingerprintBuilder()
    
    run_synthetic_validation(pipeline, engine, builder)
    run_real_profiling(pipeline, engine, builder)
