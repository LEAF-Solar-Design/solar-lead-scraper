"""
Edge case tests for scraper error handling and validation.
Run with: python -m pytest tests/test_edge_cases.py -v
"""

import sys
import json
import tempfile
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import (
    score_job,
    load_filter_config,
    categorize_rejection,
    process_jobs,
    ScoringResult,
    get_batch_slice,
)
import pandas as pd


class TestScoreJobEdgeCases:
    """Test score_job with edge case inputs."""

    def test_none_description(self):
        """score_job should handle None description gracefully."""
        result = score_job(None, "Test Company")
        assert not result.qualified
        assert "No description" in result.reasons[0] or "no description" in result.reasons[0].lower()

    def test_empty_description(self):
        """score_job should handle empty string description."""
        result = score_job("", "Test Company")
        assert not result.qualified

    def test_none_company(self):
        """score_job should handle None company name."""
        result = score_job("Solar designer role using Helioscope", None)
        # Should still process - company is optional for scoring
        assert result is not None

    def test_empty_company(self):
        """score_job should handle empty company name."""
        result = score_job("Solar designer role using Helioscope and AutoCAD", "")
        assert result is not None

    def test_nan_description(self):
        """score_job should handle pandas NaN description."""
        import pandas as pd
        result = score_job(pd.NA, "Test Company")
        assert not result.qualified

    def test_very_long_description(self):
        """score_job should handle very long descriptions."""
        # 100KB description
        long_desc = "Solar designer using Helioscope. " * 3000
        result = score_job(long_desc, "Test Company")
        assert result is not None
        assert result.qualified  # Has solar context + Helioscope


class TestLoadFilterConfig:
    """Test filter config loading and validation."""

    def test_missing_required_keys(self):
        """Config should fail validation if required keys missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"version": "1.0"}, f)
            f.flush()
            try:
                load_filter_config(Path(f.name))
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "missing required keys" in str(e).lower()

    def test_missing_patterns_in_required_context(self):
        """Config should fail if required_context missing patterns."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "company_blocklist": [],
                "required_context": {"description": "test"},
                "exclusions": {},
                "positive_signals": {}
            }, f)
            f.flush()
            try:
                load_filter_config(Path(f.name))
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "patterns" in str(e).lower()

    def test_valid_minimal_config(self):
        """Minimal valid config should load successfully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "company_blocklist": [],
                "required_context": {"patterns": ["solar"]},
                "exclusions": {},
                "positive_signals": {}
            }, f)
            f.flush()
            config = load_filter_config(Path(f.name))
            assert config is not None
            assert "company_blocklist" in config


class TestCategorizeRejection:
    """Test rejection categorization covers all exclusion types."""

    def test_sales_rejection(self):
        """Sales role rejections should categorize correctly."""
        result = ScoringResult(
            qualified=False,
            score=0,
            threshold=50,
            reasons=["Excluded: sales manager pattern"],
            company_score=0,
            role_score=0
        )
        assert categorize_rejection(result) == "exclusions.sales"

    def test_management_rejection(self):
        """Management role rejections should categorize correctly."""
        result = ScoringResult(
            qualified=False,
            score=0,
            threshold=50,
            reasons=["Excluded: project manager pattern"],
            company_score=0,
            role_score=0
        )
        assert categorize_rejection(result) == "exclusions.management"

    def test_semiconductor_rejection(self):
        """Semiconductor rejections should categorize correctly."""
        result = ScoringResult(
            qualified=False,
            score=0,
            threshold=50,
            reasons=["Excluded: semiconductor pattern"],
            company_score=0,
            role_score=0
        )
        assert categorize_rejection(result) == "exclusions.semiconductor"

    def test_space_rejection(self):
        """Space/aerospace rejections should categorize correctly."""
        result = ScoringResult(
            qualified=False,
            score=0,
            threshold=50,
            reasons=["Excluded: satellite pattern"],
            company_score=0,
            role_score=0
        )
        assert categorize_rejection(result) == "exclusions.space"

    def test_other_engineering_rejection(self):
        """Other engineering rejections should categorize correctly."""
        result = ScoringResult(
            qualified=False,
            score=0,
            threshold=50,
            reasons=["Excluded: application engineer pattern"],
            company_score=0,
            role_score=0
        )
        assert categorize_rejection(result) == "exclusions.other_engineering"

    def test_company_blocklist_rejection(self):
        """Company blocklist rejections should categorize correctly."""
        result = ScoringResult(
            qualified=False,
            score=-100,
            threshold=50,
            reasons=["Company blocked"],
            company_score=-100,
            role_score=0
        )
        assert categorize_rejection(result) == "company_blocklist"

    def test_unknown_rejection(self):
        """Unknown rejections should categorize as unknown."""
        result = ScoringResult(
            qualified=False,
            score=0,
            threshold=50,
            reasons=[],
            company_score=0,
            role_score=0
        )
        assert categorize_rejection(result) == "unknown"


class TestProcessJobs:
    """Test process_jobs with edge cases."""

    def test_empty_dataframe(self):
        """process_jobs should handle empty DataFrame."""
        df = pd.DataFrame(columns=['company', 'title', 'location', 'job_url'])
        result = process_jobs(df, {})
        assert result.empty

    def test_none_company_rows_filtered(self):
        """Rows with None company should be filtered out."""
        df = pd.DataFrame({
            'company': [None, 'Valid Company', ''],
            'title': ['Title1', 'Title2', 'Title3'],
            'location': ['Loc1', 'Loc2', 'Loc3'],
            'job_url': ['url1', 'url2', 'url3']
        })
        result = process_jobs(df, {})
        assert len(result) == 1
        assert result.iloc[0]['company'] == 'Valid Company'

    def test_duplicate_companies_deduped(self):
        """Duplicate companies should be deduplicated."""
        df = pd.DataFrame({
            'company': ['Company A', 'Company A', 'Company B'],
            'title': ['Title1', 'Title2', 'Title3'],
            'location': ['Loc1', 'Loc2', 'Loc3'],
            'job_url': ['url1', 'url2', 'url3']
        })
        result = process_jobs(df, {})
        assert len(result) == 2

    def test_confidence_scores_mapped(self):
        """Confidence scores should be properly mapped from scoring_results."""
        df = pd.DataFrame({
            'company': ['Company A'],
            'title': ['Solar Designer'],
            'location': ['NYC'],
            'job_url': ['url1']
        })
        scoring_results = {
            0: ScoringResult(
                qualified=True,
                score=75.0,
                threshold=50,
                reasons=["Tier 1 match"],
                company_score=0,
                role_score=75.0
            )
        }
        result = process_jobs(df, scoring_results)
        assert result.iloc[0]['confidence_score'] == 75.0


class TestGetBatchSlice:
    """Test batch splitting logic used by GitHub Actions matrix."""

    def test_even_split(self):
        """Items divide evenly across batches."""
        items = list(range(8))  # 8 items, 4 batches = 2 each
        assert get_batch_slice(items, 0, 4) == [0, 1]
        assert get_batch_slice(items, 1, 4) == [2, 3]
        assert get_batch_slice(items, 2, 4) == [4, 5]
        assert get_batch_slice(items, 3, 4) == [6, 7]

    def test_uneven_split(self):
        """Extra items go to earlier batches."""
        items = list(range(10))  # 10 items, 4 batches
        # 10 / 4 = 2 with remainder 2, so batches 0,1 get 3 items each
        assert get_batch_slice(items, 0, 4) == [0, 1, 2]  # 3 items
        assert get_batch_slice(items, 1, 4) == [3, 4, 5]  # 3 items
        assert get_batch_slice(items, 2, 4) == [6, 7]     # 2 items
        assert get_batch_slice(items, 3, 4) == [8, 9]     # 2 items

    def test_all_batches_cover_all_items(self):
        """All batches combined should equal original list."""
        items = list(range(65))  # Actual search term count
        total_batches = 4
        combined = []
        for batch in range(total_batches):
            combined.extend(get_batch_slice(items, batch, total_batches))
        assert combined == items
        assert len(combined) == len(items)

    def test_no_overlap_between_batches(self):
        """Batches should not share any items."""
        items = list(range(17))  # Odd number that doesn't divide evenly
        total_batches = 3
        all_items = []
        for batch in range(total_batches):
            batch_items = get_batch_slice(items, batch, total_batches)
            for item in batch_items:
                assert item not in all_items, f"Item {item} appears in multiple batches"
                all_items.append(item)

    def test_single_batch(self):
        """Single batch should return all items."""
        items = list(range(10))
        assert get_batch_slice(items, 0, 1) == items

    def test_more_batches_than_items(self):
        """Some batches will be empty if more batches than items."""
        items = [1, 2]  # 2 items, 4 batches
        assert get_batch_slice(items, 0, 4) == [1]
        assert get_batch_slice(items, 1, 4) == [2]
        assert get_batch_slice(items, 2, 4) == []
        assert get_batch_slice(items, 3, 4) == []

    def test_empty_list(self):
        """Empty list should return empty for all batches."""
        items = []
        assert get_batch_slice(items, 0, 4) == []
        assert get_batch_slice(items, 1, 4) == []
        assert get_batch_slice(items, 2, 4) == []
        assert get_batch_slice(items, 3, 4) == []

    def test_preserves_order(self):
        """Items should maintain their original order within batches."""
        items = ['a', 'b', 'c', 'd', 'e', 'f']
        result = get_batch_slice(items, 0, 2)
        assert result == ['a', 'b', 'c']  # First half
        result = get_batch_slice(items, 1, 2)
        assert result == ['d', 'e', 'f']  # Second half

    def test_invalid_batch_negative(self):
        """Negative batch should raise ValueError."""
        items = list(range(10))
        try:
            get_batch_slice(items, -1, 4)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "batch must be >= 0" in str(e)

    def test_invalid_batch_too_large(self):
        """Batch >= total_batches should raise ValueError."""
        items = list(range(10))
        try:
            get_batch_slice(items, 4, 4)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must be < total_batches" in str(e)

    def test_invalid_total_batches_zero(self):
        """total_batches=0 should raise ValueError."""
        items = list(range(10))
        try:
            get_batch_slice(items, 0, 0)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "total_batches must be >= 1" in str(e)

    def test_invalid_total_batches_negative(self):
        """Negative total_batches should raise ValueError."""
        items = list(range(10))
        try:
            get_batch_slice(items, 0, -1)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "total_batches must be >= 1" in str(e)

    def test_real_world_65_terms_4_batches(self):
        """Test with actual production values (65 search terms, 4 batches)."""
        items = list(range(65))  # Simulates 65 search terms
        # 65 / 4 = 16 with remainder 1
        # Batch 0 gets 17 items (extra), batches 1-3 get 16 each
        batch_0 = get_batch_slice(items, 0, 4)
        batch_1 = get_batch_slice(items, 1, 4)
        batch_2 = get_batch_slice(items, 2, 4)
        batch_3 = get_batch_slice(items, 3, 4)

        assert len(batch_0) == 17
        assert len(batch_1) == 16
        assert len(batch_2) == 16
        assert len(batch_3) == 16
        assert len(batch_0) + len(batch_1) + len(batch_2) + len(batch_3) == 65


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
