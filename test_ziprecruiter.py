"""
Test script for ZipRecruiter scraper.
Tests a single search to validate the fix for 0 jobs issue.
"""

import os
from pathlib import Path

# Import the scraper
from camoufox_scraper import run_camoufox_scraper, CAMOUFOX_AVAILABLE


def test_ziprecruiter():
    """Test ZipRecruiter scraper with a known good search term."""

    if not CAMOUFOX_AVAILABLE:
        print("ERROR: Camoufox not available. Install with: pip install camoufox")
        return

    # Create debug directory
    debug_dir = Path("output/debug_screenshots")
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Enable debug mode
    os.environ["CAMOUFOX_DEBUG"] = "1"

    # Test with a search term that should have results
    search_term = "solar designer"
    print(f"\n{'='*60}")
    print(f"Testing ZipRecruiter scraper")
    print(f"Search term: '{search_term}'")
    print(f"Sites: ziprecruiter only")
    print(f"Debug mode: ENABLED")
    print(f"{'='*60}\n")

    try:
        # Scrape ZipRecruiter
        jobs_df, errors, search_attempts = run_camoufox_scraper(
            search_terms=[search_term],
            sites=["ziprecruiter"],  # Only test ZipRecruiter
            debug_screenshots=True
        )

        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Jobs found: {len(jobs_df)}")
        print(f"Errors: {len(errors)}")
        print(f"Search attempts: {len(search_attempts)}")

        if len(jobs_df) > 0:
            print(f"\n[SUCCESS] ZipRecruiter returned {len(jobs_df)} jobs\n")
            print("Sample jobs:")
            for i, row in jobs_df.head(5).iterrows():
                print(f"\n  {i+1}. {row['title']}")
                print(f"     Company: {row['company']}")
                print(f"     Location: {row['location']}")
                if row.get('job_url'):
                    url_preview = row['job_url'][:80] if len(row['job_url']) > 80 else row['job_url']
                    print(f"     URL: {url_preview}{'...' if len(row['job_url']) > 80 else ''}")
        else:
            print("\n[FAILED] ZipRecruiter returned 0 jobs")
            print(f"Check debug screenshots in: {debug_dir}/")
            if errors:
                print(f"\nErrors encountered:")
                for err in errors[:3]:  # Show first 3 errors
                    print(f"  - {err.get('error_type')}: {err.get('error_message', '')[:100]}")

        print(f"\n{'='*60}\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the test
    test_ziprecruiter()
