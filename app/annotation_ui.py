"""
Streamlit Human Annotation UI for UnifAI SIH26099
Human Governance Layer
"""

import os
import tempfile
import pandas as pd
import streamlit as st
import datetime

st.set_page_config(layout="wide", page_title="UnifAI Annotation UI")

DATA_DIR = "data/real_benchmark"
QUEUE_FILE = os.path.join(DATA_DIR, "real_review_queue.csv")
ANNOTATION_FILE = os.path.join(DATA_DIR, "real_review_annotations.csv")

# Constants
RELATIONSHIPS = [
    "IDENTICAL",
    "EQUIVALENT",
    "VARIANT_OF",
    "DISTINCT",
    "UNDETERMINED"
]

EVIDENCE_TYPES = [
    "EXACT_TECHNICAL_MATCH",
    "SEMANTIC_SIMILARITY",
    "LEXICAL_MATCH",
    "DIMENSION_MATCH",
    "PRESSURE_MATCH",
    "MATERIAL_MATCH",
    "STANDARD_MATCH",
    "COMPONENT_MATCH",
    "UOM_COMPATIBILITY",
    "MPN_MATCH",
    "MANUFACTURER_MATCH",
    "ADDITIONAL_COMPATIBLE_INFORMATION",
    "TECHNICAL_CONFLICT",
    "MISSING_INFORMATION",
    "OTHER"
]

def load_data():
    if not os.path.exists(QUEUE_FILE):
        st.error(f"Review queue file not found: {QUEUE_FILE}")
        st.stop()
        
    queue_df = pd.read_csv(QUEUE_FILE)
    
    # Create pair_id if missing
    if "pair_id" not in queue_df.columns:
        queue_df["pair_id"] = queue_df["query_id"].astype(str) + "_" + queue_df["candidate_id"].astype(str)
        
    annotations_df = pd.DataFrame()
    if os.path.exists(ANNOTATION_FILE):
        annotations_df = pd.read_csv(ANNOTATION_FILE)
        
    return queue_df, annotations_df

def safe_save_annotations(annotations_df):
    """Atomically save the annotations DataFrame."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".csv")
    with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
        annotations_df.to_csv(f, index=False)
    
    # Atomic replace
    os.replace(temp_path, ANNOTATION_FILE)

def initialize_state(queue_df, annotations_df):
    if "current_index" not in st.session_state:
        # Find first unreviewed pair
        reviewed_pairs = set(annotations_df["pair_id"]) if not annotations_df.empty else set()
        first_unreviewed = 0
        for i, row in queue_df.iterrows():
            if row["pair_id"] not in reviewed_pairs:
                first_unreviewed = i
                break
        st.session_state.current_index = first_unreviewed
        st.session_state.reviewer_id = ""

def format_match(val):
    if pd.isna(val):
        return "MISSING / NOT_APPLICABLE"
    return "MATCH" if val == 1.0 or val == True else "CONFLICT"

def main():
    queue_df, annotations_df = load_data()
    initialize_state(queue_df, annotations_df)
    
    st.title("UnifAI — Real CPSE Material Relationship Review")
    st.write("Human validation of real CPSE material relationships")
    
    # Sidebar / Progress
    reviewed_count = len(annotations_df) if not annotations_df.empty else 0
    total_count = len(queue_df)
    remaining_count = total_count - reviewed_count
    progress_pct = (reviewed_count / total_count * 100) if total_count > 0 else 0
    
    st.sidebar.header("Progress Dashboard")
    st.sidebar.progress(progress_pct / 100.0)
    st.sidebar.text(f"Total pairs: {total_count}")
    st.sidebar.text(f"Reviewed: {reviewed_count}")
    st.sidebar.text(f"Remaining: {remaining_count}")
    st.sidebar.text(f"Progress: {progress_pct:.1f}%")
    
    if not annotations_df.empty:
        st.sidebar.subheader("Relationship Distribution")
        dist = annotations_df["review_relation"].value_counts()
        for rel in RELATIONSHIPS:
            st.sidebar.text(f"{rel}: {dist.get(rel, 0)}")
            
    st.sidebar.header("Export")
    if not annotations_df.empty:
        csv_data = annotations_df.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="Download Annotations (CSV)",
            data=csv_data,
            file_name="real_review_annotations.csv",
            mime="text/csv",
        )
        
    # Navigation
    st.header(f"PAIR NAVIGATION")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    def go_prev():
        if st.session_state.current_index > 0:
            st.session_state.current_index -= 1
            
    def go_next():
        if st.session_state.current_index < total_count - 1:
            st.session_state.current_index += 1

    with col1:
        st.button("Previous", on_click=go_prev)
    with col2:
        st.button("Next", on_click=go_next)
    with col3:
        jump_idx = st.number_input("Jump to Index", min_value=0, max_value=total_count-1, value=st.session_state.current_index, label_visibility="collapsed")
        if jump_idx != st.session_state.current_index:
            st.session_state.current_index = jump_idx

    current_idx = st.session_state.current_index
    if current_idx >= total_count:
        st.success("All pairs reviewed!")
        return

    row = queue_df.iloc[current_idx]
    pair_id = row["pair_id"]
    
    st.subheader(f"Current Pair ID: {pair_id} (Index: {current_idx})")
    
    # Material Panels
    mat_a_col, mat_b_col = st.columns(2)
    
    with mat_a_col:
        st.markdown("### MATERIAL A")
        st.markdown(f"**CPSE:** {row.get('query_cpse', 'N/A')}")
        st.markdown(f"**Material Code:** {row.get('query_id', 'N/A')}")
        st.markdown(f"**Description:**\n\n> {row.get('query_description', 'N/A')}")
        
    with mat_b_col:
        st.markdown("### MATERIAL B")
        st.markdown(f"**CPSE:** {row.get('candidate_cpse', 'N/A')}")
        st.markdown(f"**Material Code:** {row.get('candidate_id', 'N/A')}")
        st.markdown(f"**Description:**\n\n> {row.get('candidate_description', 'N/A')}")
        
    st.markdown("---")
    
    # Technical Comparison
    st.markdown("### SIDE-BY-SIDE TECHNICAL COMPARISON")
    st.caption("Based on automated Lane 6 evidence")
    
    comp_data = [
        {"Attribute": "Dimension", "Comparison": format_match(row.get("dimension_match"))},
        {"Attribute": "Pressure Rating", "Comparison": format_match(row.get("pressure_rating_match"))},
        {"Attribute": "Material Grade", "Comparison": format_match(row.get("material_grade_match"))},
        {"Attribute": "Standard", "Comparison": format_match(row.get("standard_match"))},
        {"Attribute": "Component Type", "Comparison": format_match(row.get("component_type_match"))},
        {"Attribute": "Manufacturer", "Comparison": format_match(row.get("manufacturer_match"))},
        {"Attribute": "MPN", "Comparison": format_match(row.get("mpn_match"))},
        {"Attribute": "UOM Compatibility", "Comparison": format_match(row.get("uom_compatibility"))}
    ]
    st.table(pd.DataFrame(comp_data))
    
    # Automated Evidence
    st.markdown("### AUTOMATED EVIDENCE — NOT GROUND TRUTH")
    st.warning("AI SYSTEM OUTPUT — DO NOT USE AS GROUND TRUTH")
    
    ev_col1, ev_col2, ev_col3 = st.columns(3)
    with ev_col1:
        st.markdown(f"**Semantic Similarity:** {row.get('semantic_similarity', 0):.4f}")
        st.markdown(f"**Lexical Similarity:** {row.get('lexical_similarity', 0):.4f}")
    with ev_col2:
        st.markdown(f"**Technical Conflict:** {bool(row.get('technical_conflict', False))}")
        st.markdown(f"**Missing Attributes:** {sum([row.get('missing_dimension', False), row.get('missing_pressure', False), row.get('missing_material', False), row.get('missing_standard', False), row.get('missing_component', False)])}")
    with ev_col3:
        st.markdown(f"**Lane 6 Relation:** {row.get('lane6_relationship', 'N/A')}")
        st.markdown(f"**Pool:** {row.get('candidate_pool', 'N/A')}")
    
    # Critical Safety Warning
    if bool(row.get('technical_conflict', False)):
        st.error("🚨 TECHNICAL CONFLICT DETECTED. Review attributes carefully.")
        
    st.markdown("---")
    
    # Human Decision Panel
    st.markdown("### HUMAN TECHNICAL REVIEW")
    
    # Check if already reviewed
    existing_review = None
    if not annotations_df.empty and pair_id in annotations_df["pair_id"].values:
        existing_review = annotations_df[annotations_df["pair_id"] == pair_id].iloc[0]
        st.info(f"Existing review found. Reviewed by {existing_review['reviewer_id']} at {existing_review['updated_at']}")
        
    with st.form("review_form"):
        st.markdown("**What is the relationship between these two materials?**")
        
        default_idx = None
        if existing_review is not None and existing_review["review_relation"] in RELATIONSHIPS:
            default_idx = RELATIONSHIPS.index(existing_review["review_relation"])
            
        selected_relation = st.radio(
            "Relationship",
            RELATIONSHIPS,
            index=default_idx,
            key="relation_radio"
        )
        
        default_evidence = []
        if existing_review is not None and pd.notna(existing_review.get("review_evidence_types")):
            default_evidence = [e.strip() for e in existing_review["review_evidence_types"].split(",") if e.strip() in EVIDENCE_TYPES]
            
        selected_evidence = st.multiselect(
            "Primary Evidence (Select at least one)",
            EVIDENCE_TYPES,
            default=default_evidence
        )
        
        default_notes = existing_review["review_notes"] if existing_review is not None and pd.notna(existing_review["review_notes"]) else ""
        notes = st.text_area("Reviewer Notes", value=default_notes, help="Explain the technical reason for the selected relationship.")
        
        default_reviewer = existing_review["reviewer_id"] if existing_review is not None else st.session_state.reviewer_id
        reviewer_id = st.text_input("Reviewer ID", value=default_reviewer)
        
        submitted = st.form_submit_button("SUBMIT REVIEW & NEXT")
        
        if submitted:
            if selected_relation is None:
                st.error("You must select a relationship.")
            elif not selected_evidence:
                st.error("You must select at least one evidence type.")
            elif not reviewer_id.strip():
                st.error("You must provide a Reviewer ID.")
            else:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                st.session_state.reviewer_id = reviewer_id
                
                new_row = {
                    "pair_id": pair_id,
                    "query_id": row["query_id"],
                    "candidate_id": row["candidate_id"],
                    "review_status": "REVIEWED",
                    "review_relation": selected_relation,
                    "reviewer_id": reviewer_id,
                    "created_at": existing_review["created_at"] if existing_review is not None else now,
                    "updated_at": now,
                    "review_evidence_types": ",".join(selected_evidence),
                    "review_notes": notes
                }
                
                if not annotations_df.empty and pair_id in annotations_df["pair_id"].values:
                    # Update
                    annotations_df.loc[annotations_df["pair_id"] == pair_id, list(new_row.keys())] = list(new_row.values())
                else:
                    # Append
                    new_df = pd.DataFrame([new_row])
                    annotations_df = pd.concat([annotations_df, new_df], ignore_index=True)
                    
                safe_save_annotations(annotations_df)
                st.success("Saved!")
                go_next()
                st.rerun()

if __name__ == "__main__":
    main()
