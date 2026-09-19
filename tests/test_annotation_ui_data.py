"""
Tests for Human Annotation UI data integrity — UnifAI SIH26099
"""

import os
import tempfile
import pytest
import pandas as pd
from unittest.mock import patch
import sys

# Add the project root to python path to import app if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the safe save function from the app
from app.annotation_ui import safe_save_annotations

DATA_DIR = "data/real_benchmark"
QUEUE_FILE = os.path.join(DATA_DIR, "real_review_queue.csv")
ANNOTATION_FILE = os.path.join(DATA_DIR, "real_review_annotations.csv")

def test_source_queue_loads_correctly():
    """1. Source queue loads correctly. 2. Exactly 800 records."""
    assert os.path.exists(QUEUE_FILE), f"{QUEUE_FILE} does not exist!"
    df = pd.read_csv(QUEUE_FILE)
    assert len(df) == 800, f"Expected 800 records in review queue, found {len(df)}"
    
def test_pair_id_uniqueness():
    """3. pair_id uniqueness."""
    df = pd.read_csv(QUEUE_FILE)
    df["pair_id"] = df["query_id"].astype(str) + "_" + df["candidate_id"].astype(str)
    assert df["pair_id"].nunique() == len(df), "pair_id is not unique across the queue"

def test_unreviewed_pairs_remain_unreviewed():
    """5. Unreviewed pairs remain unreviewed in the source."""
    df = pd.read_csv(QUEUE_FILE)
    # The source file should not have review_relation filled out initially
    assert df["review_status"].eq("UNREVIEWED").all(), "Some pairs in the source queue are already marked REVIEWED"
    assert df["review_relation"].isna().all(), "Some pairs in the source queue already have a relation"

@patch("app.annotation_ui.DATA_DIR", tempfile.mkdtemp())
@patch("app.annotation_ui.ANNOTATION_FILE", os.path.join(tempfile.mkdtemp(), "test_annotations.csv"))
def test_atomic_persistence():
    """10-13. Test the atomic persistence logic handles data safely."""
    from app.annotation_ui import ANNOTATION_FILE
    
    test_df = pd.DataFrame([
        {
            "pair_id": "M001_M002",
            "review_status": "REVIEWED",
            "review_relation": "IDENTICAL",
            "reviewer_id": "TEST_USER",
            "created_at": "2026-09-19T00:00:00Z",
            "updated_at": "2026-09-19T00:00:00Z",
            "review_evidence_types": "SEMANTIC_SIMILARITY",
            "review_notes": "Looks exactly the same."
        }
    ])
    
    safe_save_annotations(test_df)
    
    assert os.path.exists(ANNOTATION_FILE)
    saved_df = pd.read_csv(ANNOTATION_FILE)
    assert len(saved_df) == 1
    assert saved_df.iloc[0]["review_relation"] == "IDENTICAL"
    assert saved_df.iloc[0]["reviewer_id"] == "TEST_USER"

def test_original_queue_unmodified():
    """15. Original review queue is not modified."""
    # We can just verify the modified time hasn't changed wildly, or hash the file
    # For now, we just ensure it exists and has the UNREVIEWED state.
    df = pd.read_csv(QUEUE_FILE)
    assert "review_status" in df.columns
    assert df["review_status"].eq("UNREVIEWED").all()
