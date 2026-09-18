import os
import pandas as pd
import json

archive_dir = "archive/data"
audit_results = []

def classify_file(filepath):
    # Determine classification based on path and name
    if "corpus" in filepath:
        return "REAL_PUBLIC_SOURCE"
    elif "erp_mocks" in filepath:
        return "ERP_MOCK"
    elif "benchmark" in filepath:
        return "LABELLED_BENCHMARK" if "benchmark" in filepath else "DERIVED/PROCESSED_DATA"
    elif "reference" in filepath:
        return "REFERENCE_DATA"
    return "UNKNOWN"

for root, dirs, files in os.walk(archive_dir):
    for f in files:
        filepath = os.path.join(root, f)
        rel_path = os.path.relpath(filepath, "archive/data")
        size = os.path.getsize(filepath)
        
        info = {
            "filename": f,
            "location": filepath,
            "format": f.split('.')[-1] if '.' in f else "unknown",
            "approximate_size_bytes": size,
            "classification": classify_file(filepath)
        }
        
        if f.endswith('.csv'):
            try:
                df = pd.read_csv(filepath)
                info["row_count"] = len(df)
                info["columns"] = df.columns.tolist()
            except Exception as e:
                info["row_count"] = "error"
                info["columns"] = []
        else:
            info["row_count"] = "N/A (not CSV)"
            info["columns"] = []
            
        audit_results.append(info)

os.makedirs("data/metadata", exist_ok=True)
with open("data/metadata/archive_data_audit.json", "w") as f:
    json.dump(audit_results, f, indent=4)
    
print("Audit complete.")
