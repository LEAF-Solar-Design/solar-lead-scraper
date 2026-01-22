"""
Deep test script for ZipRecruiter scraper.
Tests multiple pages and search terms to validate production-level performance.
"""

import os
import time
from pathlib import Path

# Import the scraper
from camoufox_scraper import run_camoufox_scraper, CAMOUFOX_AVAILABLE


def test_ziprecruiter_deep():
    """Test ZipRecruiter scraper with multiple search terms and deep pagination."""

    if not CAMOUFOX_AVAILABLE:
        print("ERROR: Camoufox not available. Install with: pip install camoufox")
        return

    # Create debug directory
    debug_dir = Path("output/debug_screenshots")
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Enable debug mode
    os.environ["CAMOUFOX_DEBUG"] = "1"

    # Test with multiple search terms that should have results
    search_terms = [
        "solar designer",
        "solar engineer",
        "pvsyst",
    ]

    print(f"\n{'='*60}")
    print(f"DEEP TEST: ZipRecruiter Scraper")
    print(f"{'='*60}")
    print(f"Search terms: {len(search_terms)} terms")
    print(f"Sites: ziprecruiter only")
    print(f"Debug mode: ENABLED")
    print(f"Pagination: FULL (multiple pages per search)")
    print(f"{'='*60}\n")

    start_time = time.time()

    try:
        # Scrape ZipRecruiter with multiple terms
        jobs_df, errors, search_attempts = run_camoufox_scraper(
            search_terms=search_terms,
            sites=["ziprecruiter"],  # Only test ZipRecruiter
            debug_screenshots=True
        )

        elapsed_time = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Total time: {elapsed_time:.1f}s")
        print(f"Jobs found: {len(jobs_df)}")
        print(f"Search terms: {len(search_terms)}")
        print(f"Avg jobs per search: {len(jobs_df) / len(search_terms):.1f}")
        print(f"Avg time per search: {elapsed_time / len(search_terms):.1f}s")
        print(f"Errors: {len(errors)}")
        print(f"Search attempts logged: {len(search_attempts)}")

        # Analyze search attempts
        if search_attempts:
            print(f"\n{'='*60}")
            print(f"SEARCH ATTEMPT DETAILS")
            print(f"{'='*60}")
            for attempt in search_attempts:
                term = attempt.get('search_term', 'unknown')
                jobs_found = attempt.get('jobs_found', 0)
                duration = attempt.get('duration_ms', 0)
                success = attempt.get('success', False)
                status = '[SUCCESS]' if success else '[FAILED]'
                print(f"{status} '{term}': {jobs_found} jobs in {duration}ms")

        if len(jobs_df) > 0:
            print(f"\n{'='*60}")
            print(f"[SUCCESS] ZipRecruiter returned {len(jobs_df)} total jobs")
            print(f"{'='*60}\n")

            # Show breakdown by search term
            print("Jobs by search term:")
            for term in search_terms:
                term_jobs = jobs_df[jobs_df['search_term'] == term]
                print(f"  '{term}': {len(term_jobs)} jobs")

            # Show sample jobs from each search term
            print(f"\nSample jobs (first 2 from each search):")
            for term in search_terms:
                term_jobs = jobs_df[jobs_df['search_term'] == term]
                if len(term_jobs) > 0:
                    print(f"\n  Search: '{term}'")
                    for i, row in term_jobs.head(2).iterrows():
                        print(f"    - {row['title']}")
                        print(f"      Company: {row['company']}")
                        print(f"      Location: {row['location']}")
                else:
                    print(f"\n  Search: '{term}' - No jobs found")

            # Show job URL sample to verify links work
            print(f"\nSample job URLs (first 3):")
            for i, row in jobs_df.head(3).iterrows():
                if row.get('job_url'):
                    url_preview = row['job_url'][:80] if len(row['job_url']) > 80 else row['job_url']
                    print(f"  {i+1}. {url_preview}{'...' if len(row['job_url']) > 80 else ''}")

            # Check for descriptions
            jobs_with_desc = len([j for _, j in jobs_df.iterrows() if j.get('description') and len(j['description']) > 50])
            print(f"\nJobs with descriptions: {jobs_with_desc}/{len(jobs_df)} ({jobs_with_desc/len(jobs_df)*100:.1f}%)")

        else:
            print(f"\n[FAILED] ZipRecruiter returned 0 jobs")
            print(f"Check debug screenshots in: {debug_dir}/")
            if errors:
                print(f"\nErrors encountered:")
                for err in errors[:5]:  # Show first 5 errors
                    print(f"  - {err.get('error_type')}: {err.get('error_message', '')[:100]}")

        print(f"\n{'='*60}\n")

        # Compare with expected baseline
        expected_avg_jobs = 20  # Based on single-page test returning 20
        actual_avg_jobs = len(jobs_df) / len(search_terms) if len(search_terms) > 0 else 0

        print(f"PERFORMANCE ASSESSMENT:")
        print(f"  Expected avg: ~{expected_avg_jobs} jobs/search (single page baseline)")
        print(f"  Actual avg: {actual_avg_jobs:.1f} jobs/search")

        if actual_avg_jobs >= expected_avg_jobs * 0.8:
            print(f"  Status: [SUCCESS] Within expected range")
        elif actual_avg_jobs > 0:
            print(f"  Status: [WARNING] Below expected range but finding jobs")
        else:
            print(f"  Status: [FAILED] Not finding any jobs")

        print()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the deep test
    test_ziprecruiter_deep()
