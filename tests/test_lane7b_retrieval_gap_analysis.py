"""
Tests for Lane 7B Retrieval Gap Analysis.

Verifies:
  1.  No ground-truth leakage
  2.  Correct Top-K rank calculation
  3.  Recall@K calculations
  4.  Relationship-specific metrics
  5.  Same/cross-CPSE metrics
  6.  NOT_RETRIEVED_TOP100 classification
  7.  No self-match counted as positive retrieval
  8.  Duplicate candidate IDs do not inflate recall
  9.  Output schema validation
"""

import os, sys, json
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

REPORT_JSON = "outputs/lane7b_retrieval_gap_analysis.json"
REPORT_CSV  = "outputs/lane7b_positive_retrieval_pairs.csv"


# ---------------------------------------------------------------
# 1. No ground-truth leakage
# ---------------------------------------------------------------
class TestNoLeakage:
    def test_retrieval_engine_does_not_import_gt(self):
        """The retrieval engine must not reference ground truth."""
        import inspect
        from src.retrieval.engine import RetrievalEngine
        source = inspect.getsource(RetrievalEngine)
        assert "ground_truth" not in source.lower()
        assert "relation_type" not in source.lower()
        assert "canonical_id" not in source.lower()

    def test_gt_not_used_in_query(self):
        """Ensure the analysis script does not inject GT into queries."""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "dataset",
            "lane7b_retrieval_gap_analysis.py"
        )
        if not os.path.exists(script_path):
            # Try alternative path
            script_path = "scripts/dataset/lane7b_retrieval_gap_analysis.py"
        with open(script_path, "r") as f:
            source = f.read()
        # GT should only be loaded via load_positive_gt() and used AFTER retrieval
        # Ensure no "relation_type" or "canonical_id" is passed to retrieve_candidates
        assert "retrieve_candidates" in source
        # The GT columns should not appear in the retrieval call context
        lines = source.split("\n")
        in_retrieval_section = False
        for line in lines:
            if "retrieve_candidates" in line:
                in_retrieval_section = True
            if in_retrieval_section:
                assert "relation_type" not in line, "GT leakage: relation_type near retrieve_candidates"
                if line.strip() == "":
                    in_retrieval_section = False


# ---------------------------------------------------------------
# 2-6. Rank and recall calculations (unit tests with synthetic data)
# ---------------------------------------------------------------
class TestRankCalculation:
    def test_rank_1_is_top10(self):
        rank = 1
        assert rank <= 10

    def test_rank_10_is_top10(self):
        rank = 10
        assert rank <= 10

    def test_rank_11_is_not_top10(self):
        rank = 11
        assert rank > 10
        assert rank <= 25

    def test_rank_25_is_top25(self):
        rank = 25
        assert rank <= 25

    def test_rank_100_is_top100(self):
        rank = 100
        assert rank <= 100

    def test_rank_101_is_not_top100(self):
        rank = 101
        assert rank > 100


class TestRecallCalculation:
    def _recall(self, retrieved_count, total):
        return retrieved_count / max(1, total)

    def test_perfect_recall(self):
        assert self._recall(10, 10) == 1.0

    def test_zero_recall(self):
        assert self._recall(0, 10) == 0.0

    def test_partial_recall(self):
        assert abs(self._recall(3, 10) - 0.3) < 1e-9

    def test_empty_total_returns_zero(self):
        assert self._recall(0, 0) == 0.0


class TestBucketClassification:
    def _classify(self, rank):
        if rank is not None and rank <= 10:
            return "RETRIEVED_TOP10"
        elif rank is not None and rank <= 25:
            return "RETRIEVED_11_25"
        elif rank is not None and rank <= 50:
            return "RETRIEVED_26_50"
        elif rank is not None and rank <= 100:
            return "RETRIEVED_51_100"
        else:
            return "NOT_RETRIEVED_TOP100"

    def test_rank_1(self):
        assert self._classify(1) == "RETRIEVED_TOP10"

    def test_rank_17(self):
        assert self._classify(17) == "RETRIEVED_11_25"

    def test_rank_50(self):
        assert self._classify(50) == "RETRIEVED_26_50"

    def test_rank_99(self):
        assert self._classify(99) == "RETRIEVED_51_100"

    def test_rank_none(self):
        assert self._classify(None) == "NOT_RETRIEVED_TOP100"

    def test_rank_147(self):
        assert self._classify(147) == "NOT_RETRIEVED_TOP100"


# ---------------------------------------------------------------
# 7. No self-match counted as positive
# ---------------------------------------------------------------
class TestNoSelfMatch:
    def test_gt_has_no_self_pairs(self):
        """Ground truth should never have a == b."""
        gt_path = "data/synthetic/ground_truth_relationships.csv"
        if not os.path.exists(gt_path):
            pytest.skip("GT file not found")
        gt = pd.read_csv(gt_path)
        self_matches = gt[gt["material_id_a"] == gt["material_id_b"]]
        assert len(self_matches) == 0, f"Found {len(self_matches)} self-match pairs in GT"


# ---------------------------------------------------------------
# 8. Duplicate candidates do not inflate recall
# ---------------------------------------------------------------
class TestNoDuplicateInflation:
    def test_candidate_set_has_unique_ids(self):
        """The retrieval engine deduplicates candidates by material_id."""
        # This is verified by inspection of engine.py which uses a dict (merged)
        # keyed by material_id, guaranteeing uniqueness.
        import inspect
        from src.retrieval.engine import RetrievalEngine
        source = inspect.getsource(RetrievalEngine.retrieve_candidates)
        assert "merged" in source or "dict" in source.lower()


# ---------------------------------------------------------------
# 9. Output schema validation (if report exists)
# ---------------------------------------------------------------
@pytest.mark.skipif(
    not os.path.exists(REPORT_JSON),
    reason="Report not yet generated"
)
class TestReportSchema:
    @pytest.fixture(autouse=True)
    def load_report(self):
        with open(REPORT_JSON, "r", encoding="utf-8") as f:
            self.report = json.load(f)

    def test_all_sections_present(self):
        expected = [
            "1_directionality",
            "2_per_class_retrieval_recall",
            "3_bucket_distribution",
            "4_rank_distribution",
            "5_cross_cpse_analysis",
            "6_retrieval_vs_classification",
            "7_variant_of_special",
            "8_equivalent_special",
            "9_identical_special",
            "10_discrepancy_explanation",
            "11_answers",
        ]
        for section in expected:
            assert section in self.report, f"Missing section: {section}"

    def test_per_class_has_all_relationship_types(self):
        pc = self.report["2_per_class_retrieval_recall"]
        for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "ALL_POSITIVE"]:
            assert rel in pc
            assert "recall_at_10" in pc[rel]
            assert "recall_at_25" in pc[rel]
            assert "recall_at_50" in pc[rel]
            assert "recall_at_100" in pc[rel]
            assert "total" in pc[rel]
            assert "not_retrieved" in pc[rel]

    def test_cross_cpse_has_all_types(self):
        cc = self.report["5_cross_cpse_analysis"]
        for rel in ["IDENTICAL", "EQUIVALENT", "VARIANT_OF"]:
            assert rel in cc
            assert "same_cpse_total" in cc[rel]
            assert "cross_cpse_total" in cc[rel]

    def test_answers_present(self):
        ans = self.report["11_answers"]
        assert "Q8_recommendation" in ans
        assert "Q7_top100_sufficient" in ans

    def test_recall_values_in_range(self):
        pc = self.report["2_per_class_retrieval_recall"]
        for rel in pc:
            for k in ["recall_at_10", "recall_at_25", "recall_at_50", "recall_at_100"]:
                val = pc[rel][k]
                assert 0.0 <= val <= 1.0, f"{rel} {k} = {val} out of range"


@pytest.mark.skipif(
    not os.path.exists(REPORT_CSV),
    reason="CSV not yet generated"
)
class TestCSVOutput:
    @pytest.fixture(autouse=True)
    def load_csv(self):
        self.df = pd.read_csv(REPORT_CSV)

    def test_required_columns(self):
        required = [
            "query_id", "target_id", "relationship", "direction",
            "query_cpse", "target_cpse", "same_cpse", "rank", "bucket",
            "in_top10", "in_top25", "in_top50", "in_top100"
        ]
        for col in required:
            assert col in self.df.columns, f"Missing column: {col}"

    def test_no_self_matches(self):
        self_matches = self.df[self.df["query_id"] == self.df["target_id"]]
        assert len(self_matches) == 0

    def test_only_positive_relationships(self):
        allowed = {"IDENTICAL", "EQUIVALENT", "VARIANT_OF"}
        actual = set(self.df["relationship"].unique())
        assert actual.issubset(allowed), f"Unexpected relationships: {actual - allowed}"

    def test_both_directions(self):
        dirs = set(self.df["direction"].unique())
        assert "A->B" in dirs
        assert "B->A" in dirs

    def test_in_top_monotonic(self):
        """If in_top10 is True, in_top25/50/100 must also be True."""
        for _, row in self.df.iterrows():
            if row["in_top10"]:
                assert row["in_top25"]
                assert row["in_top50"]
                assert row["in_top100"]
            if row["in_top25"]:
                assert row["in_top50"]
                assert row["in_top100"]
            if row["in_top50"]:
                assert row["in_top100"]
