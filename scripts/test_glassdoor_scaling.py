"""
Comprehensive scaling test for Glassdoor anti-scraping bypass.
Tests multiple search terms to ensure strategies work at scale.
"""

import asyncio
import time
from camoufox.async_api import AsyncCamoufox
from camoufox_scraper import scrape_glassdoor_page


async def test_multiple_searches():
    """Test with multiple search terms to validate scaling."""

    # Use a variety of search terms (subset from actual search list)
    test_terms = [
        "solar designer",
        "PV designer",
        "photovoltaic engineer",
        "CAD designer solar",
        "electrical designer"
    ]

    print("="*80)
    print("GLASSDOOR SCALING TEST")
    print("="*80)
    print(f"\nTesting with {len(test_terms)} search terms")
    print("Strategy: 5 descriptions per search with random delays\n")

    async with AsyncCamoufox(headless=True, humanize=True, disable_coop=True) as browser:

        results = []
        total_start = time.time()

        for i, term in enumerate(test_terms, 1):
            print(f"\n[{i}/{len(test_terms)}] Testing: '{term}'")
            print("-" * 60)

            search_start = time.time()

            try:
                jobs = await scrape_glassdoor_page(
                    browser,
                    term,
                    max_descriptions=5
                )

                search_elapsed = time.time() - search_start

                # Count successes
                jobs_with_desc = sum(1 for j in jobs if j.get('description') and len(j.get('description', '')) > 50)
                success_rate = (jobs_with_desc / 5) * 100 if jobs_with_desc > 0 else 0

                results.append({
                    'term': term,
                    'total_jobs': len(jobs),
                    'with_descriptions': jobs_with_desc,
                    'success_rate': success_rate,
                    'time': search_elapsed
                })

                print(f"  Results: {len(jobs)} jobs found")
                print(f"  Descriptions: {jobs_with_desc}/5 ({success_rate:.0f}% success)")
                print(f"  Time: {search_elapsed:.1f}s")

            except Exception as e:
                print(f"  ERROR: {str(e)[:100]}")
                results.append({
                    'term': term,
                    'total_jobs': 0,
                    'with_descriptions': 0,
                    'success_rate': 0,
                    'time': time.time() - search_start,
                    'error': str(e)[:100]
                })

        total_elapsed = time.time() - total_start

        # Analysis
        print("\n" + "="*80)
        print("SCALING ANALYSIS")
        print("="*80)

        successful_searches = [r for r in results if 'error' not in r]

        if successful_searches:
            avg_time = sum(r['time'] for r in successful_searches) / len(successful_searches)
            avg_success = sum(r['success_rate'] for r in successful_searches) / len(successful_searches)
            total_desc = sum(r['with_descriptions'] for r in successful_searches)

            print(f"\nPer-Search Metrics:")
            print(f"  Avg time: {avg_time:.1f}s")
            print(f"  Avg success rate: {avg_success:.0f}%")
            print(f"  Total descriptions fetched: {total_desc}/{len(successful_searches)*5}")

            # Check variance
            times = [r['time'] for r in successful_searches]
            min_time = min(times)
            max_time = max(times)
            variance = max_time - min_time

            print(f"\nTiming Consistency:")
            print(f"  Min: {min_time:.1f}s")
            print(f"  Max: {max_time:.1f}s")
            print(f"  Variance: {variance:.1f}s ({variance/avg_time*100:.0f}% of avg)")

            if variance / avg_time < 0.3:
                print("  Assessment: CONSISTENT (low variance)")
            elif variance / avg_time < 0.5:
                print("  Assessment: MODERATE (acceptable variance)")
            else:
                print("  Assessment: HIGH VARIANCE (may indicate issues)")

            # Success rate consistency
            success_rates = [r['success_rate'] for r in successful_searches]
            min_success = min(success_rates)
            max_success = max(success_rates)

            print(f"\nSuccess Rate Consistency:")
            print(f"  Min: {min_success:.0f}%")
            print(f"  Max: {max_success:.0f}%")
            print(f"  Range: {max_success - min_success:.0f} percentage points")

            if all(sr >= 60 for sr in success_rates):
                print("  Assessment: RELIABLE (all searches >60%)")
            elif avg_success >= 60:
                print("  Assessment: ACCEPTABLE (avg >60% but some variance)")
            else:
                print("  Assessment: UNRELIABLE (avg <60%)")

        # Projection to full run
        print(f"\n" + "="*80)
        print("FULL RUN PROJECTION (21 searches)")
        print("="*80)

        if successful_searches:
            projected_time = avg_time * 21
            projected_desc = (avg_success / 100) * 5 * 21

            print(f"\nProjected metrics:")
            print(f"  Total time: {projected_time:.1f}s ({projected_time/60:.1f} min)")
            print(f"  Expected descriptions: {projected_desc:.0f}/105")
            print(f"  Expected success rate: {avg_success:.0f}%")

            print(f"\nComparison to baseline (Run #38):")
            baseline_time = 94.8  # minutes
            projected_time_min = projected_time / 60
            savings = baseline_time - projected_time_min
            savings_pct = (savings / baseline_time) * 100

            print(f"  Baseline: {baseline_time:.1f} min")
            print(f"  Projected: {projected_time_min:.1f} min")
            print(f"  Savings: {savings:.1f} min ({savings_pct:.0f}%)")

            # Quality assessment
            print(f"\n" + "="*80)
            print("QUALITY ASSESSMENT")
            print("="*80)

            if avg_success >= 80 and variance / avg_time < 0.3:
                print("\nRESULT: EXCELLENT")
                print("  - High success rate (>80%)")
                print("  - Consistent timing")
                print("  - Ready for production")
            elif avg_success >= 70 and variance / avg_time < 0.5:
                print("\nRESULT: GOOD")
                print("  - Acceptable success rate (>70%)")
                print("  - Reasonable consistency")
                print("  - Suitable for production with monitoring")
            elif avg_success >= 60:
                print("\nRESULT: ACCEPTABLE")
                print("  - Marginal success rate (60-70%)")
                print("  - May need additional optimization")
            else:
                print("\nRESULT: NEEDS IMPROVEMENT")
                print("  - Low success rate (<60%)")
                print("  - Consider alternative strategies")

        # Detailed results table
        print(f"\n" + "="*80)
        print("DETAILED RESULTS")
        print("="*80)
        print(f"\n{'Search Term':<30} | Time | Desc | Success")
        print("-" * 80)
        for r in results:
            if 'error' in r:
                print(f"{r['term']:<30} | ERROR: {r['error'][:30]}")
            else:
                print(f"{r['term']:<30} | {r['time']:4.0f}s | {r['with_descriptions']}/5  | {r['success_rate']:6.0f}%")

        print("\n" + "="*80)
        print(f"Total test time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(test_multiple_searches())
