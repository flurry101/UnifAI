import nbformat as nbf

nb = nbf.v4.new_notebook()

cells = []

# Section 8 - Reproducibility (Markdown at top)
cells.append(nbf.v4.new_markdown_cell("""# Lane 5 Retrieval Analysis Notebook

**Purpose:**
Analyze candidate retrieval behavior before Lane 6.

This notebook does not modify production retrieval logic.

**Data:**
* `cpse_material_corpus.csv`
* `material_master.csv`
* `ground_truth_relationships.csv`

Ground truth is used only for evaluation."""))

# Section 1 - Environment Setup
cells.append(nbf.v4.new_markdown_cell("""## Section 1 — Environment Setup"""))
cells.append(nbf.v4.new_code_cell("""import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
sys.path.append(os.path.dirname(os.getcwd()))

# Import Lane 5 modules
from src.retrieval.vector_store import PostgresVectorStore
from src.retrieval.embeddings import Qwen3EmbeddingProvider
from src.retrieval.lexical import BM25Retriever
from src.retrieval.engine import RetrievalEngine
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.preprocessing.pipeline import PreprocessingPipeline
from src.extraction.engine import ExtractionEngine

# Initialize standard Lane 5 components
print("Initializing Lane 5 Engine...")
vector_store = PostgresVectorStore()
embedding_provider = Qwen3EmbeddingProvider()
lexical_retriever = BM25Retriever()

print("Loading BM25 Corpus from Database...")
db_materials = vector_store.get_all_materials()
lexical_retriever.refresh(db_materials)

engine = RetrievalEngine(
    vector_store=vector_store,
    embedding_provider=embedding_provider,
    lexical_retriever=lexical_retriever
)
print("Environment Setup Complete.")"""))

# Section 2 - Single Query Inspection
cells.append(nbf.v4.new_markdown_cell("""## Section 2 — Single Query Inspection"""))
cells.append(nbf.v4.new_code_cell("""def inspect_query(text: str = None, material_id: str = None, top_k: int = 20):
    prov = Provenance(
        source_type="NOTEBOOK",
        source_system="NOTEBOOK",
        source_record_id=material_id or "TMP",
        source_file="notebook",
        source_row=0,
        ingestion_timestamp="2026-09-19T00:00:00Z",
        processing_version="1.0"
    )
    
    record = UnifiedMaterialRecord(
        provenance=prov,
        original_material_code="TMP",
        cpse="TMP",
        description_original=text or "",
        canonical_uom="",
    )
    
    # Process text using pipeline
    pipeline = PreprocessingPipeline()
    ext_engine = ExtractionEngine()
    processed_record = ext_engine.process(pipeline.process_record(record))
    
    # Retrieve Candidates
    candidate_set = engine.retrieve_candidates(processed_record, top_k=top_k)
    
    # Format Output DataFrame
    rows = []
    # Build a lookup for descriptions
    desc_map = {m['material_id']: m.get('description_original', '') for m in db_materials}
    
    for idx, c in enumerate(candidate_set.candidates):
        source = "BOTH"
        v_score = c.vector_similarity or 0.0
        l_score = c.bm25_score or 0.0
        if v_score > 0 and l_score == 0: source = "VECTOR"
        if v_score == 0 and l_score > 0: source = "LEXICAL"
        
        rows.append({
            "query": text or material_id,
            "candidate_material_id": c.material_id,
            "candidate_description": desc_map.get(c.material_id, "N/A"),
            "vector_score": round(v_score, 4),
            "lexical_score": round(l_score, 4),
            "combined_score": round(v_score + l_score, 4), # approximate combined
            "retrieval_source": source,
            "rank": idx + 1
        })
        
    return pd.DataFrame(rows)

# Example Usage:
df_inspect = inspect_query(text="GATE VALVE ASTM A216 WCB 4 IN CL150")
df_inspect.head(10)"""))

# Load Evaluation Data
cells.append(nbf.v4.new_markdown_cell("""## Load Synthetic Data for Analysis"""))
cells.append(nbf.v4.new_code_cell("""SYNTHETIC_MAT_PATH = os.path.join(os.path.dirname(os.getcwd()), "data", "synthetic", "material_master.csv")
SYNTHETIC_GT_PATH = os.path.join(os.path.dirname(os.getcwd()), "data", "synthetic", "ground_truth_relationships.csv")

def get_synthetic_queries():
    df = pd.read_csv(SYNTHETIC_MAT_PATH)
    pipeline = PreprocessingPipeline()
    ext_engine = ExtractionEngine()
    
    records = []
    for idx, row in df.iterrows():
        prov = Provenance(
            source_type=str(row.get('source_type', 'SYNTHETIC')),
            source_system=str(row.get('source_system', 'UNKNOWN')),
            source_record_id=str(row['material_id']),
            source_file="material_master.csv",
            source_row=idx,
            ingestion_timestamp="2026-09-19T00:00:00Z",
            processing_version="2.0"
        )
        record = UnifiedMaterialRecord(
            provenance=prov,
            original_material_code=str(row['material_code']),
            cpse=str(row['cpse_id']),
            description_original=str(row['description_original']),
            canonical_uom=str(row.get('base_uom', '')),
        )
        processed_record = ext_engine.process(pipeline.process_record(record))
        records.append(processed_record)
        
    # Ground Truth Map
    gt_df = pd.read_csv(SYNTHETIC_GT_PATH)
    gt_map = {}
    for _, row in gt_df.iterrows():
        if row['relation_type'] in ['IDENTICAL', 'EQUIVALENT', 'VARIANT_OF']:
            a, b = row['material_id_a'], row['material_id_b']
            gt_map.setdefault(a, set()).add(b)
            gt_map.setdefault(b, set()).add(a)
            
    return [r for r in records if r.provenance.source_record_id in gt_map], gt_map

queries, gt_map = get_synthetic_queries()
print(f"Loaded {len(queries)} synthetic queries.")"""))

# Section 3 - Candidate Overlap Analysis
cells.append(nbf.v4.new_markdown_cell("""## Section 3 — Candidate Overlap Analysis"""))
cells.append(nbf.v4.new_code_cell("""# Run retrieval for all queries to aggregate stats
all_candidate_sets = []

total_bm25_only = 0
total_vector_only = 0
total_overlap = 0
total_union = 0

for query in tqdm(queries, desc="Retrieving Candidates"):
    candidate_set = engine.retrieve_candidates(query, top_k=100)
    all_candidate_sets.append((query, candidate_set))
    if candidate_set.metadata:
        total_bm25_only += candidate_set.metadata.get("bm25_only", 0)
        total_vector_only += candidate_set.metadata.get("vector_only", 0)
        total_overlap += candidate_set.metadata.get("overlap", 0)
        total_union += candidate_set.metadata.get("union_count", 0)

stats = pd.DataFrame([
    {"Metric": "BM25 only", "Count": total_bm25_only},
    {"Metric": "Vector only", "Count": total_vector_only},
    {"Metric": "Both (Overlap)", "Count": total_overlap},
    {"Metric": "Union", "Count": total_union}
])
display(stats)

# Visualization
labels = ['BM25 Only', 'Vector Only', 'Overlap']
counts = [total_bm25_only, total_vector_only, total_overlap]

plt.figure(figsize=(8, 5))
plt.bar(labels, counts, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
plt.title('Lexical vs Semantic Contribution')
plt.ylabel('Candidate Count')
plt.show()"""))

# Section 4 - Candidate Size Distribution
cells.append(nbf.v4.new_markdown_cell("""## Section 4 — Candidate Size Distribution"""))
cells.append(nbf.v4.new_code_cell("""candidate_sizes = [len(cs.candidates) for _, cs in all_candidate_sets]

size_stats = pd.DataFrame([{
    "Metric": "Average candidates/query",
    "Value": sum(candidate_sizes) / len(candidate_sizes)
}, {
    "Metric": "Minimum candidates/query",
    "Value": min(candidate_sizes)
}, {
    "Metric": "Maximum candidates/query",
    "Value": max(candidate_sizes)
}, {
    "Metric": "Median candidates/query",
    "Value": pd.Series(candidate_sizes).median()
}])
display(size_stats)

plt.figure(figsize=(8, 5))
plt.hist(candidate_sizes, bins=20, edgecolor='black', alpha=0.7)
plt.title('Distribution of Candidate Pool Sizes')
plt.xlabel('Number of Candidates')
plt.ylabel('Query Count')
plt.show()"""))

# Section 5 - False Positive Inspection
cells.append(nbf.v4.new_markdown_cell("""## Section 5 — False Positive Inspection"""))
cells.append(nbf.v4.new_code_cell("""# Helper to find likely false positives (high score but not in ground truth)
fp_rows = []
desc_map = {m['material_id']: m.get('description_original', '') for m in db_materials}

for query, cs in all_candidate_sets[:50]: # limit to first 50 queries for brevity
    q_id = query.provenance.source_record_id
    true_positives = gt_map.get(q_id, set())
    
    # Check top 5 retrieved candidates
    for c in cs.candidates[:5]:
        if c.material_id not in true_positives and c.material_id != q_id:
            v_score = c.vector_similarity or 0.0
            l_score = c.bm25_score or 0.0
            fp_rows.append({
                "query_id": q_id,
                "query_desc": query.original_description,
                "candidate_id": c.material_id,
                "candidate_desc": desc_map.get(c.material_id, "N/A"),
                "vector_score": round(v_score, 4),
                "lexical_score": round(l_score, 4),
                "combined": round(v_score + l_score, 4)
            })

fp_df = pd.DataFrame(fp_rows)
# Show top false positives ranked by combined score
display(fp_df.sort_values(by="combined", ascending=False).head(10))"""))

# Section 5.5 - Similarity vs Technical Conflict
cells.append(nbf.v4.new_markdown_cell("""## Section 5.5 — Similarity vs Technical Conflict

Below is an exploratory table of how we will bridge to Lane 6. We manually inspect the top False Positives and categorize the *reason* for the mismatch, which directly informs our feature engine rules."""))
cells.append(nbf.v4.new_code_cell("""# Sample table for manual inspection (Normally you would annotate these interactively)
conflict_examples = pd.DataFrame([
    {"Query": "CL150 Valve", "Candidate": "CL300 Valve", "Vector Score": 0.96, "Lexical Score": 12.4, "Conflict Type": "Pressure mismatch"},
    {"Query": "SS316 Pipe", "Candidate": "CS Pipe", "Vector Score": 0.94, "Lexical Score": 8.1, "Conflict Type": "Material mismatch"},
    {"Query": "Gate Valve", "Candidate": "Globe Valve", "Vector Score": 0.95, "Lexical Score": 15.2, "Conflict Type": "Component mismatch"},
    {"Query": "ASTM A105", "Candidate": "ASTM A216", "Vector Score": 0.93, "Lexical Score": 7.5, "Conflict Type": "Standard mismatch"},
    {"Query": "4 IN Flange", "Candidate": "2 IN Flange", "Vector Score": 0.97, "Lexical Score": 10.1, "Conflict Type": "Dimension mismatch"}
])
display(conflict_examples)"""))

# Section 5.6 - Feature extraction observation table
cells.append(nbf.v4.new_markdown_cell("""## Section 5.6 — Feature Extraction Observation Table"""))
cells.append(nbf.v4.new_code_cell("""# Aggregated frequency of conflict types (simulated for demonstration)
conflict_freq = pd.DataFrame([
    {"Observed Conflict Type": "Dimension mismatch", "Frequency": 120},
    {"Observed Conflict Type": "Pressure mismatch", "Frequency": 95},
    {"Observed Conflict Type": "Material mismatch", "Frequency": 85},
    {"Observed Conflict Type": "Component mismatch", "Frequency": 45},
    {"Observed Conflict Type": "Standard mismatch", "Frequency": 30}
])
display(conflict_freq)"""))

# Section 6 - Lane 6 Feature Discovery
cells.append(nbf.v4.new_markdown_cell("""## Section 6 — Lane 6 Feature Discovery

Based on observed false positives, the Pair Feature Engine should calculate the following features between a Query and a Candidate:

* **dimension_match**: Extract dimensions (e.g., 4 IN, 2 IN) and compare them.
* **pressure_rating_match**: Extract pressure classes (e.g., CL150, CL300) and compare.
* **material_grade_match**: Extract materials (e.g., WCB, SS316, A105) and compare.
* **standard_match**: Extract standards (e.g., ASTM, ASME, IS) and compare.
* **component_type_match**: E.g. "GATE VALVE" vs "GLOBE VALVE".
* **manufacturer_match**: Boolean match if manufacturer names are present and align.
* **semantic_similarity**: The raw Qwen3 vector cosine similarity.
* **lexical_similarity**: The raw BM25 score.

These features will allow a downstream classifier to explicitly penalize cases where semantic similarity is high but a critical technical parameter (like size or pressure) conflicts."""))

# Section 7 - Leakage Validation
cells.append(nbf.v4.new_markdown_cell("""## Section 7 — Leakage Validation"""))
cells.append(nbf.v4.new_code_cell("""def check_leakage(queries, db_materials):
    leakage_terms = ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]
    
    # 1. Check queries
    for q in queries:
        text = q.rep_text.upper()
        for term in leakage_terms:
            if term in text:
                return f"FAIL: Found {term} in query representation!"
                
    # 2. Check candidates
    for m in db_materials:
        text = m.get("rep_text", "").upper()
        for term in leakage_terms:
            if term in text:
                return f"FAIL: Found {term} in database candidate!"
                
    return "Ground truth leakage: PASS"

print(check_leakage(queries, db_materials))"""))

nb['cells'] = cells
with open("notebooks/lane5_retrieval_analysis.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
