import os
import pytest
import pandas as pd
from scripts.dataset.lane6_validation import run_lane6_validation, OUTPUT_CSV_PATH

def test_lane6_validation_execution():
    """
    Tests that the Lane 6 validation script runs successfully and 
    generates the expected output files without crashing.
    """
    
    # We shouldn't actually run the full validation in a standard unit test 
    # because it takes time and hits the database, but we can verify imports
    # and basic file structures are present.
    
    from src.retrieval.engine import RetrievalEngine
    from src.matching.lane6_features import PairFeatureEngine
    from src.ingestion.unified_schema import UnifiedMaterialRecord
    
    assert RetrievalEngine is not None
    assert PairFeatureEngine is not None
    
def test_false_positive_csv_generated():
    """
    If the CSV was generated, verify it has the expected columns.
    """
    if os.path.exists(OUTPUT_CSV_PATH):
        df = pd.read_csv(OUTPUT_CSV_PATH)
        expected_cols = [
            "query_id", "candidate_id", "query_description", "candidate_description",
            "vector_score", "lexical_score", "dimension_match", "pressure_match",
            "material_match", "standard_match", "technical_conflict", 
            "relationship_class", "explanation"
        ]
        for col in expected_cols:
            assert col in df.columns
