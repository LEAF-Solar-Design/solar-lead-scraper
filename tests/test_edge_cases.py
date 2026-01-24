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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
