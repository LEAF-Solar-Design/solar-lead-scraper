"""
Upload scraper results to the ops-dashboard.
Called by GitHub Actions after scraping completes.
"""

import os
import glob
import requests


def get_latest_csv():
    """Find the most recent CSV file in output directory by filename date."""
    csv_files = glob.glob("output/solar_leads_*.csv")
    if not csv_files:
        raise FileNotFoundError("No CSV files found in output/")
    # Sort by filename (which contains timestamp) to get the latest
    return max(csv_files)


def upload_to_dashboard(csv_path: str):
    """Upload CSV to the dashboard API."""
    dashboard_url = os.environ.get("DASHBOARD_URL")
    api_key = os.environ.get("DASHBOARD_API_KEY")

    if not dashboard_url:
        raise ValueError("DASHBOARD_URL environment variable not set")
    if not api_key:
        raise ValueError("DASHBOARD_API_KEY environment variable not set")

    # Read CSV content
    with open(csv_path, "r") as f:
        csv_content = f.read()

    # POST to dashboard API
    url = f"{dashboard_url.rstrip('/')}/api/jobs/ingest"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "text/csv",
    }

    print(f"Uploading {csv_path} to {url}")
    response = requests.post(url, data=csv_content, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Success! Imported {result.get('count', '?')} leads")
        return result
    else:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        raise Exception(f"Upload failed with status {response.status_code}")


def main():
    csv_path = get_latest_csv()
    print(f"Found latest CSV: {csv_path}")
    upload_to_dashboard(csv_path)


if __name__ == "__main__":
    main()
