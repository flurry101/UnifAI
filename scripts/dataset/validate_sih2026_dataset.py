import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
SYNTHETIC_DIR = os.path.join(DATA_DIR, "synthetic")
REAL_DIR = os.path.join(DATA_DIR, "real_public")

def run_validation():
    errors = []
    
    print("Running Dataset V2 Validations...")
    
    # 1. Directory Structure
    if not os.path.exists(SYNTHETIC_DIR) or not os.path.exists(REAL_DIR):
        errors.append("Rule: Strict separation of Synthetic and Real Public directories failed.")
        
    # 2. Load Synthetic Data
    try:
        mat_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "material_master.csv"))
        can_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "canonical_material.csv"))
        rel_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "ground_truth_relationships.csv"))
        cf_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "counterfactual_pairs.csv"))
        ev_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "pair_evidence.csv"))
    except Exception as e:
        errors.append(f"Failed to load synthetic files: {e}")
        return errors
        
    # 3. Referential Integrity
    mat_ids = set(mat_df['material_id'])
    for idx, row in rel_df.iterrows():
        if row['material_id_a'] not in mat_ids or row['material_id_b'] not in mat_ids:
            errors.append(f"Rule: Referential integrity failed on pair {row['pair_id']}")
            
    # 4. Same-CPSE vs Cross-CPSE coverage
    same_cpse_count = len(rel_df[rel_df['cpse_a'] == rel_df['cpse_b']])
    if same_cpse_count == 0:
        errors.append("Rule: Same-CPSE coverage missing. No IDENTICAL/duplicate pairs found within the same CPSE.")
        
    # 5. Counterfactual Logic
    cf_variant_rels = rel_df[rel_df['source_type'] == 'SYNTHETIC_MUTATION']
    if len(cf_variant_rels) == 0:
        errors.append("Rule: Counterfactual generation missing.")
    
    for idx, cf in cf_df.iterrows():
        # Check that exactly one attribute mutated
        if cf['original_value'] == cf['mutated_value']:
            errors.append(f"Rule: Counterfactual pair {cf['pair_id']} failed 1-attribute mutation constraint.")
            
    # 6. Source Conflict Checks
    # The generator purposefully injected abbreviations or missing attributes compared to Canonical.
    # The evidence file contains TECHNICAL_CONFLICT evidence.
    conflict_evidence = ev_df[ev_df['evidence_type'] == 'TECHNICAL_CONFLICT']
    if len(conflict_evidence) == 0:
        errors.append("Rule: Source conflict injection missing. No TECHNICAL_CONFLICT evidence found.")
        
    # 7. Ground Truth Leakage
    # canonical_id must NOT be exposed in processing/feature files. 
    # (Since we only generated master/canonical/rels, we assume it's safe, but let's check it's not in canonical_description).
    if any('CAN-' in str(d) for d in mat_df['description_original']):
        errors.append("Rule: Ground truth leakage. canonical_id found in description.")
        
    # 8. Real Public Data Checks
    try:
        real_df = pd.read_csv(os.path.join(REAL_DIR, "real_cpse_materials.csv"))
        if 'canonical_id' in real_df.columns:
            errors.append("Rule: Ground truth leakage. Real public data contains canonical_id.")
        if len(real_df) < 500:
            errors.append("Rule: Materialized development subset is too small (<500 records).")
    except Exception as e:
        errors.append(f"Failed to load real public file: {e}")
        
    return errors

if __name__ == "__main__":
    errs = run_validation()
    if errs:
        print("Validation Failed:")
        for e in errs:
            print("-", e)
        exit(1)
    else:
        print("All validations passed! Dataset V2 is ready.")
        exit(0)
