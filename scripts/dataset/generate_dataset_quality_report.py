import os
import json
import pandas as pd
import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
SYNTHETIC_DIR = os.path.join(DATA_DIR, "synthetic")
REAL_DIR = os.path.join(DATA_DIR, "real_public")
META_DIR = os.path.join(DATA_DIR, "metadata")

def generate_reports():
    os.makedirs(META_DIR, exist_ok=True)
    
    try:
        mat_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "material_master.csv"))
        can_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "canonical_material.csv"))
        rel_df = pd.read_csv(os.path.join(SYNTHETIC_DIR, "ground_truth_relationships.csv"))
        real_df = pd.read_csv(os.path.join(REAL_DIR, "real_cpse_materials.csv"))
    except Exception as e:
        print("Error loading files:", e)
        return
        
    # Dataset Quality Report
    quality_report = {
        "generation_timestamp": datetime.datetime.now().isoformat(),
        "synthetic_data_stats": {
            "canonical_materials": len(can_df),
            "material_renderings": len(mat_df),
            "total_relationships": len(rel_df),
            "relationship_distribution": rel_df['relation_type'].value_counts().to_dict(),
            "hard_negatives": len(rel_df[rel_df['difficulty'] == 'HARD']),
            "missing_attribute_counts": mat_df.isnull().sum().to_dict()
        },
        "real_data_stats": {
            "development_subset_records": len(real_df),
            "missing_attribute_counts": real_df.isnull().sum().to_dict()
        }
    }
    
    with open(os.path.join(META_DIR, "dataset_quality_report.json"), "w") as f:
        json.dump(quality_report, f, indent=4)
        
    # Update Metadata
    metadata = {
        "version": "2.0",
        "description": "UnifAI SIH 2026 Dataset V2",
        "schema_type": "Unified",
        "files": {
            "synthetic": ["canonical_material.csv", "material_master.csv", "ground_truth_relationships.csv", "counterfactual_pairs.csv", "pair_evidence.csv"],
            "real_public": ["real_cpse_materials.csv"]
        },
        "notes": [
            "Synthetic data generated with hard negatives and counterfactuals.",
            "Real public data sampled from the 21K corpus for testing.",
            "Both datasets follow the unified preprocessing schema."
        ],
        "generation_date": datetime.datetime.now().isoformat()
    }
    
    with open(os.path.join(META_DIR, "dataset_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)
        
    print("Generated quality report and metadata.")

if __name__ == "__main__":
    generate_reports()
