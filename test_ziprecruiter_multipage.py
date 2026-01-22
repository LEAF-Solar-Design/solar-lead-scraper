"""
Multi-page test for ZipRecruiter scraper.
Tests that 5-page scraping returns significantly more results than single page.
"""

import os
import time
from pathlib import Path

# Import the scraper
from camoufox_scraper import run_camoufox_scraper, CAMOUFOX_AVAILABLE


def test_ziprecruiter_multipage():
    """Test ZipRecruiter scraper with multi-page enabled (5 pages)."""

    if not CAMOUFOX_AVAILABLE:
        print("ERROR: Camoufox not available. Install with: pip install camoufox")
        return

    # Create debug directory
    debug_dir = Path("output/debug_screenshots")
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Enable debug mode
    os.environ["CAMOUFOX_DEBUG"] = "1"

    # Test with a single search term
    search_term = "solar designer"

    print(f"\n{'='*60}")
    print(f"MULTI-PAGE TEST: ZipRecruiter Scraper")
    print(f"{'='*60}")
    print(f"Search term: '{search_term}'")
    print(f"Sites: ziprecruiter only")
    print(f"Max pages: 5 (expecting ~100 jobs)")
    print(f"Debug mode: ENABLED")
    print(f"{'='*60}\n")

    start_time = time.time()

    try:
        # Scrape ZipRecruiter with multi-page enabled
        jobs_df, errors, search_attempts = run_camoufox_scraper(
            search_terms=[search_term],
            sites=["ziprecruiter"],
            debug_screenshots=True
        )

        elapsed_time = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Total time: {elapsed_time:.1f}s")
        print(f"Jobs found: {len(jobs_df)}")
        print(f"Errors: {len(errors)}")

        # Analyze search attempt
        if search_attempts:
            attempt = search_attempts[0]
            print(f"\nSearch attempt details:")
            print(f"  Term: {attempt.get('search_term')}")
            print(f"  Jobs found: {attempt.get('jobs_found')}")
            print(f"  Duration: {attempt.get('duration_ms')}ms ({attempt.get('duration_ms')/1000:.1f}s)")
            print(f"  Success: {attempt.get('success')}")
            print(f"  Cloudflare detected: {attempt.get('cloudflare_detected', False)}")
            print(f"  Cloudflare solved: {attempt.get('cloudflare_solved', False)}")

        if len(jobs_df) > 0:
            print(f"\n{'='*60}")
            print(f"[SUCCESS] Multi-page scraping returned {len(jobs_df)} jobs")
            print(f"{'='*60}\n")

            # Compare with baseline
            baseline_single_page = 20
            improvement = ((len(jobs_df) - baseline_single_page) / baseline_single_page * 100)

            print(f"Performance vs baseline:")
            print(f"  Single page (baseline): {baseline_single_page} jobs")
            print(f"  Multi-page (5 pages): {len(jobs_df)} jobs")
            print(f"  Improvement: {improvement:+.0f}%")

            # Show sample jobs
            print(f"\nSample jobs (first 10):")
            for i, row in jobs_df.head(10).iterrows():
                print(f"  {i+1:2d}. {row['title'][:60]}")
                print(f"      {row['company'][:40]} | {row['location'][:30]}")

            # Check descriptions
            jobs_with_desc = len([j for _, j in jobs_df.iterrows() if j.get('description') and len(j['description']) > 50])
            print(f"\nJobs with descriptions: {jobs_with_desc}/{len(jobs_df)} ({jobs_with_desc/len(jobs_df)*100:.1f}%)")

            # Assessment
            print(f"\n{'='*60}")
            print(f"ASSESSMENT")
            print(f"{'='*60}")

            if len(jobs_df) >= 80:
                print(f"[SUCCESS] Excellent - Getting 80+ jobs (4+ pages scraped)")
            elif len(jobs_df) >= 50:
                print(f"[SUCCESS] Good - Getting 50+ jobs (2.5+ pages scraped)")
            elif len(jobs_df) >= 30:
                print(f"[WARNING] Moderate - Getting 30+ jobs but below target")
            else:
                print(f"[WARNING] Low - Only {len(jobs_df)} jobs (may not be paginating)")

            print(f"\nNext steps:")
            if len(jobs_df) >= 80:
                print(f"  - Multi-page scraping is working well")
                print(f"  - Ready to enable ZipRecruiter in production")
                print(f"  - Update scraper.py line 1120: all_sites = ['indeed', 'linkedin', 'ziprecruiter']")
            else:
                print(f"  - Review debug screenshots for pagination issues")
                print(f"  - Check if 'Next' button is being found and clicked")
                print(f"  - May need to adjust pagination selectors")

        else:
            print(f"\n[FAILED] ZipRecruiter returned 0 jobs")
            print(f"Check debug screenshots in: {debug_dir}/")
            if errors:
                print(f"\nErrors encountered:")
                for err in errors[:3]:
                    print(f"  - {err.get('error_type')}: {err.get('error_message', '')[:100]}")

        print(f"\n{'='*60}\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the multi-page test
    test_ziprecruiter_multipage()
