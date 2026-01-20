"""Quick test script for Camoufox browser scraping only."""

import asyncio
import os
import sys
from pathlib import Path

# Set environment variables for browser scraping
os.environ["ENABLE_BROWSER_SCRAPING"] = "1"
os.environ["CAMOUFOX_DEBUG"] = "1"

print("Importing camoufox_scraper...", flush=True)
from camoufox_scraper import scrape_with_camoufox
print("Import complete.", flush=True)

async def main():
    # Just one search term to test quickly
    test_terms = [
        "solar designer",
    ]

    print("=" * 50, flush=True)
    print("Testing Camoufox Browser Scraping", flush=True)
    print(f"Search terms: {test_terms}", flush=True)
    print("=" * 50, flush=True)

    # Create output directory for screenshots
    output_dir = Path("output/debug_screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nStarting browser scraping (this may take a moment)...", flush=True)

    # Run browser scraping
    df, errors = await scrape_with_camoufox(
        search_terms=test_terms,
        sites=["ziprecruiter", "glassdoor"],  # Test both sites
        debug_screenshots=True
    )

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    if not df.empty:
        print(f"\nFound {len(df)} jobs total:")
        print(f"  - Glassdoor: {len(df[df['source_site'] == 'glassdoor'])}")
        print(f"  - ZipRecruiter: {len(df[df['source_site'] == 'ziprecruiter'])}")
        print("\nSample jobs:")
        print(df[['company', 'title', 'source_site']].head(10).to_string(index=False))
    else:
        print("\nNo jobs found!")

    if errors:
        print(f"\n{len(errors)} errors occurred:")
        for err in errors:
            print(f"  - [{err.site}] {err.search_term}: {err.error_type}")

    print("\nDebug screenshots saved to: output/debug_screenshots/")

if __name__ == "__main__":
    asyncio.run(main())
