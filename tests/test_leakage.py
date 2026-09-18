import os
import pytest
import pandas as pd
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SYNTHETIC_DIR = os.path.join(DATA_DIR, "synthetic")

def test_leakage_no_ground_truth_in_features():
    df_mat = pd.read_csv(os.path.join(SYNTHETIC_DIR, "material_master.csv"))
    
    # Assert that canonical_id is not masquerading as a feature or implicitly encoded
    for col in df_mat.columns:
        if col not in ['canonical_id', 'material_id', 'cpse_id', 'material_code']:
            assert not df_mat[col].astype(str).str.contains('CAN-').any(), f"Leakage found! canonical_id leaked into feature column {col}"
            
    # Also assert none of the labels are directly in the input text
    for val in df_mat['description_original']:
        val_str = str(val).upper()
        assert 'IDENTICAL' not in val_str
        assert 'EQUIVALENT' not in val_str
        assert 'VARIANT_OF' not in val_str
        assert 'UNDETERMINED' not in val_str

def test_leakage_real_public_data():
    real_df = pd.read_csv(os.path.join(DATA_DIR, "real_public", "real_cpse_materials.csv"))
    assert 'canonical_id' not in real_df.columns, "Leakage found! canonical_id present in real public data."
