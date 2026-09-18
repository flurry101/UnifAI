import os
import json

# Read the generated audit
with open("data/metadata/archive_data_audit.json", "r") as f:
    audit_data = json.load(f)

# 1. Create docs/archive-data-audit.md
md_lines = ["# Full Archive Audit Report", "", "This document details the audit of all archived datasets in the repository, assessing their readiness for Dataset V2 and the UnifAI matching architecture.", ""]

for d in audit_data:
    md_lines.append(f"## File: {d['filename']}")
    md_lines.append(f"- **Location:** `{d['location']}`")
    md_lines.append(f"- **Format:** {d['format']}")
    md_lines.append(f"- **Size:** {d['approximate_size_bytes']} bytes")
    md_lines.append(f"- **Row Count:** {d['row_count']}")
    md_lines.append(f"- **Classification:** `{d['classification']}`")
    md_lines.append(f"- **Columns:** {', '.join(d.get('columns', []))}")
    
    # Assess capabilities based on classification
    c = d['classification']
    md_lines.append(f"- **Contains Descriptions:** {'Yes' if c in ['REAL_PUBLIC_SOURCE', 'ERP_MOCK', 'LABELLED_BENCHMARK'] else 'Varies'}")
    md_lines.append(f"- **Contains Tech Attributes:** {'Yes' if c in ['REAL_PUBLIC_SOURCE', 'LABELLED_BENCHMARK'] else 'Varies'}")
    md_lines.append(f"- **Supports Normalization:** {'Yes' if c == 'REAL_PUBLIC_SOURCE' else 'No'}")
    md_lines.append(f"- **Supports Attribute Extraction:** {'Yes' if c == 'REAL_PUBLIC_SOURCE' else 'No'}")
    md_lines.append(f"- **Supports Retrieval:** {'Yes' if c == 'REAL_PUBLIC_SOURCE' else 'No'}")
    md_lines.append("")

os.makedirs("docs", exist_ok=True)
with open("docs/archive-data-audit.md", "w") as f:
    f.write("\n".join(md_lines))

# 2. Create archive_utilization_report.json
utilization = []
for d in audit_data:
    status = "OBSOLETE"
    rec = "Do not use"
    reason = "Outdated structure"
    stage = "N/A"
    
    if d['classification'] == 'REAL_PUBLIC_SOURCE':
        status = "PROCESSING_INPUT"
        rec = "Use for normalization, attribute extraction, and realistic domain patterns."
        reason = "Contains ~21K real material descriptions from CPSEs."
        stage = "Normalization & Retrieval"
    elif d['classification'] == 'ERP_MOCK':
        status = "REFERENCE"
        rec = "Use to design synthetic SAP/ERP schema fields."
        reason = "Demonstrates realistic enterprise object structures (MATMAS)."
        stage = "Synthetic Benchmark Schema"
    elif d['classification'] == 'REFERENCE_DATA':
        status = "REFERENCE"
        rec = "Use for standardizing attributes during normalization."
        reason = "Valuable taxonomy and dimension mappings."
        stage = "Normalization"
    elif d['classification'] == 'LABELLED_BENCHMARK':
        status = "ARCHIVE_ONLY"
        rec = "Keep for historical provenance."
        reason = "V1 benchmark does not support the exact V2 architecture."
        stage = "Archive"
        
    utilization.append({
        "dataset": d['location'],
        "status": status,
        "recommended_use": rec,
        "reason": reason,
        "new_architecture_stage": stage
    })

with open("data/metadata/archive_utilization_report.json", "w") as f:
    json.dump(utilization, f, indent=4)

# 3. Create data_lineage.json
lineage = {
    "real_corpus_lineage": {
        "source_dataset": "archive/data/corpus/cpse_material_corpus.csv",
        "processing_stages": [
            "raw description",
            "normalized_materials",
            "extracted_attributes",
            "fingerprints",
            "retrieval_corpus"
        ],
        "benchmark_usage": "Used for hard-negative inspiration and domain patterns."
    },
    "synthetic_benchmark_lineage": {
        "source_dataset": "Controlled synthetic generation (scripts/dataset/generate_sih2026_dataset.py)",
        "processing_stages": [
            "synthetic_canonical_materials",
            "synthetic_material_master",
            "normalized_materials",
            "extracted_attributes",
            "fingerprints",
            "labelled_pairs"
        ],
        "benchmark_usage": "Supervised pair validation and ML ranking ground truth."
    }
}

with open("data/metadata/data_lineage.json", "w") as f:
    json.dump(lineage, f, indent=4)
    
print("Generated all audit reports.")
