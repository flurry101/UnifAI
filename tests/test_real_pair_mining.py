"""
Tests for Real Pair Mining — UnifAI SIH26099

Tests the real_candidate_pairs.csv and real_review_queue.csv outputs.
These tests verify data integrity without requiring re-running the mining pipeline.
"""

import os, sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

PAIRS_PATH = "data/real_benchmark/real_candidate_pairs.csv"
REVIEW_PATH = "data/real_benchmark/real_review_queue.csv"
SYNTHETIC_GT = "data/synthetic/ground_truth_relationships.csv"


@pytest.fixture(scope="module")
def pairs_df():
    if not os.path.exists(PAIRS_PATH):
        pytest.skip("Real pair mining output not yet generated")
    return pd.read_csv(PAIRS_PATH)


@pytest.fixture(scope="module")
def review_df():
    if not os.path.exists(REVIEW_PATH):
        pytest.skip("Real review queue not yet generated")
    return pd.read_csv(REVIEW_PATH)


# 1. No self matches
class TestNoSelfMatches:
    def test_no_self_match(self, pairs_df):
        assert (pairs_df["query_id"] == pairs_df["candidate_id"]).sum() == 0


# 2. All IDs exist (non-empty)
class TestIDsExist:
    def test_query_ids_non_empty(self, pairs_df):
        assert pairs_df["query_id"].notna().all()
        assert (pairs_df["query_id"].astype(str).str.len() > 0).all()

    def test_candidate_ids_non_empty(self, pairs_df):
        assert pairs_df["candidate_id"].notna().all()
        assert (pairs_df["candidate_id"].astype(str).str.len() > 0).all()


# 3. No synthetic records
class TestNoSyntheticRecords:
    def test_no_synthetic_ids(self, pairs_df):
        if os.path.exists(SYNTHETIC_GT):
            syn = pd.read_csv(SYNTHETIC_GT)
            syn_ids = set(syn["material_id_a"].astype(str)) | set(syn["material_id_b"].astype(str))
            # Synthetic IDs should not appear (they use different ID format)
            pair_ids = set(pairs_df["query_id"].astype(str)) | set(pairs_df["candidate_id"].astype(str))
            # Check for synthetic-format IDs (MAT-xxxx pattern)
            syn_pattern_ids = {i for i in pair_ids if i.startswith("MAT-")}
            assert len(syn_pattern_ids) == 0, f"Synthetic IDs found: {syn_pattern_ids}"


# 4. No ground-truth fields used
class TestNoGroundTruthLeakage:
    def test_no_gt_columns(self, pairs_df):
        banned = ["ground_truth", "true_relation", "relation_type", "target"]
        for col in pairs_df.columns:
            for b in banned:
                assert b not in col.lower(), f"Ground truth field found: {col}"


# 5. Duplicate pair handling
class TestDuplicatePairs:
    def test_no_exact_duplicate_rows(self, pairs_df):
        key_cols = ["query_id", "candidate_id"]
        assert pairs_df.duplicated(subset=key_cols).sum() == 0


# 6. Directional pair handling is deterministic
class TestDirectionalPairs:
    def test_canonical_direction(self, pairs_df):
        """Each (A,B) pair should appear in only one direction."""
        pair_keys = set()
        for _, row in pairs_df.iterrows():
            key = tuple(sorted([str(row["query_id"]), str(row["candidate_id"])]))
            assert key not in pair_keys, f"Duplicate directional pair: {key}"
            pair_keys.add(key)


# 7. CPSE provenance preserved
class TestCPSEProvenance:
    def test_query_cpse_present(self, pairs_df):
        assert "query_cpse" in pairs_df.columns

    def test_candidate_cpse_present(self, pairs_df):
        assert "candidate_cpse" in pairs_df.columns


# 8. Automated signals separate from human labels
class TestSignalSeparation:
    def test_review_columns_exist(self, review_df):
        assert "review_relation" in review_df.columns
        assert "review_status" in review_df.columns
        assert "reviewer_notes" in review_df.columns

    def test_automated_columns_exist(self, pairs_df):
        auto_cols = ["semantic_similarity", "lexical_similarity",
                     "technical_conflict", "dimension_match"]
        for col in auto_cols:
            assert col in pairs_df.columns


# 9. Initial review_status is UNREVIEWED
class TestReviewStatusInitial:
    def test_all_unreviewed(self, review_df):
        assert (review_df["review_status"] == "UNREVIEWED").all()


# 10. Initial review_relation is NULL
class TestReviewRelationInitial:
    def test_all_null(self, review_df):
        assert review_df["review_relation"].isna().all()


# 11. Technical conflict information preserved
class TestConflictPreserved:
    def test_conflict_column_exists(self, pairs_df):
        assert "technical_conflict" in pairs_df.columns

    def test_conflict_is_boolean(self, pairs_df):
        assert pairs_df["technical_conflict"].isin([True, False, 0, 1]).all()


# 12. Missing values are not converted into conflicts
class TestMissingNotConflict:
    def test_missing_dimension_not_conflict(self, pairs_df):
        """If dimension_match is NaN, dimension_conflict should not be True."""
        # dimension_match=NaN means both sides missing → missing_dimension=True
        # This should NOT cause technical_conflict from dimension alone
        missing_dim = pairs_df[pairs_df["dimension_match"].isna()]
        if len(missing_dim) > 0:
            # We can't directly check dimension_conflict (not in output),
            # but verify that missing alone doesn't force technical_conflict
            # There should exist at least SOME missing-dim pairs without conflict
            no_conflict = missing_dim[missing_dim["technical_conflict"] == False]
            assert len(no_conflict) > 0, \
                "All dimension-missing pairs have technical conflict — suggests missing→conflict conversion"


# 13. Deterministic sampling
class TestDeterministicSampling:
    def test_fixed_seed(self):
        """The script uses RANDOM_STATE=42."""
        from scripts.dataset.real_data_variation_analysis import RANDOM_STATE
        assert RANDOM_STATE == 42


# 14. All candidate pools have valid definitions
class TestPoolDefinitions:
    def test_pool_column_exists(self, pairs_df):
        assert "candidate_pool" in pairs_df.columns

    def test_valid_pool_labels(self, pairs_df):
        for pools in pairs_df["candidate_pool"]:
            if pools == "NONE":
                continue
            for p in pools.split(","):
                assert p in "ABCDEFGH", f"Invalid pool label: {p}"


# 15. Output schema stability
class TestOutputSchema:
    def test_required_columns(self, pairs_df):
        required = [
            "query_id", "candidate_id", "query_cpse", "candidate_cpse",
            "query_description", "candidate_description",
            "semantic_similarity", "lexical_similarity",
            "technical_conflict", "cross_cpse", "fingerprint_match",
            "candidate_pool",
        ]
        for col in required:
            assert col in pairs_df.columns, f"Missing required column: {col}"

    def test_review_schema(self, review_df):
        required = [
            "query_id", "candidate_id", "review_relation",
            "review_status", "reviewer_notes",
        ]
        for col in required:
            assert col in review_df.columns, f"Missing review column: {col}"
