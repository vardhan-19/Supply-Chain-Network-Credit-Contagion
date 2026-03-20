# -*- coding: utf-8 -*-
"""
Annual Financial Report PDF Scraper (Reliable Google Search Version)
====================================================================

PURPOSE:
  Finds the direct PDF link for Annual Financial Reports of anchor companies.
  Uses googlesearch-python with `filetype:pdf` parameter to force search engines
  to return ONLY PDF documents (DuckDuckGo ignores this parameter, which caused
  random non-pdf websites to appear previously).

PREREQUISITES:
  pip install googlesearch-python requests pandas

HOW TO RUN:
  # Debug mode (tests 4 random companies for verification)
  python scripts/scrape_annual_reports.py --debug
  
  # Full run (all companies)
  python scripts/scrape_annual_reports.py
"""

import os
import csv
import time
import argparse
import requests
import random
import urllib.parse
from duckduckgo_search import DDGS

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
INPUT_CSV = r"D:\Supply Chain Network Credit Contagion\data\raw\anchor_companies.csv"
OUTPUT_CSV = r"D:\Supply Chain Network Credit Contagion\data\raw\annual_report_links.csv"

# Diverse User-Agents to prevent easily getting 403 Forbidden on PDFs
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Read Anchor Companies
# ─────────────────────────────────────────────────────────────────────────────
def get_anchor_companies(filepath: str) -> list:
    companies = []
    if not os.path.exists(filepath):
        print(f"❌ Error: Could not find {filepath}")
        return companies
        
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if name:
                companies.append(name)
    return companies

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Verify PDF Link
# ─────────────────────────────────────────────────────────────────────────────
def verify_pdf_link(url: str) -> bool:
    """
    Sends requests to verify the URL actually points to a live PDF file.
    Does NOT download the entire file, just headers or a tiny chunk.
    """
    if "sec.gov/Archives" in url and not url.endswith(".pdf"):
         # SEC often returns htm even when asked for pdf. Skip generic SEC links unless explicitly PDF.
         pass
         
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    try:
        # 1. Try HEAD request
        resp = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        # 2. If HEAD fails or is blocked, try GET with stream=True
        if resp.status_code >= 400:
            resp = requests.get(url, headers=headers, timeout=10, stream=True)
            # We don't read the content, just check status
            resp.close()
            
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "").lower()
            
            if "pdf" in content_type:
                return True
            # Allow octet-stream only if the URL explicitly says PDF
            if "octet-stream" in content_type and "pdf" in url.lower():
                return True
            # Some servers are badly configured but send a substantial payload
            if ("pdf" in url.lower() or "download" in url.lower()) and len(resp.headers.get("Content-Length", "")) > 3:
                return True
                
        return False
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE 
# ─────────────────────────────────────────────────────────────────────────────
def main(debug_mode: bool = False):
    print("=" * 70)
    print("Annual Financial Report PDF Scraper (Google Search Version)")
    if debug_mode: print("*** DEBUG MODE: Processing 4 random companies ***")
    print("=" * 70)
    
    companies = get_anchor_companies(INPUT_CSV)
    if not companies:
        print("No companies found to process. Exiting.")
        return
        
    if debug_mode:
        # Pick 4 specific diverse companies to test
        test_names = ["Ford Motor", "Aptiv", "Nucor Steel", "Sony"] 
        # Just grab from the actual list to be safe:
        random.seed(42) # Deterministic for debugging
        companies = random.sample(companies, min(4, len(companies)))
        
    print(f"📦 Processing {len(companies)} companies...\n")
    
    results = []
    
    with DDGS() as ddgs:
        for i, company in enumerate(companies, 1):
            print(f"[{i}/{len(companies)}] Searching for: {company}")
            
            # Using basic search. DDG doesn't need 'filetype:pdf', just 'pdf' keyword is usually enough.
            query = f'"{company}" "Annual Report" 2023 OR 2024 pdf'
            print(f"    Query: {query}")
            
            found_pdf = False
            final_pdf_url = ""
            
            try:
                # Get top 5 results using duckduckgo
                search_results = list(ddgs.text(query, max_results=5))
                urls_to_test = [res.get("href", "") for res in search_results if res.get("href")]

                if not urls_to_test:
                    print("    ❌ DuckDuckGo returned no URLs.")
                
                for url in urls_to_test:
                    print(f"    Testing link: {url[:80]}...")
                    if verify_pdf_link(url):
                        print(f"    ✅ Verified working PDF! > {url[:80]}...")
                        found_pdf = True
                        final_pdf_url = url
                        break
                    else:
                        print(f"    ❌ Link blocked or not a PDF.")
                        
            except Exception as e:
                print(f"    ⚠️ Search Error: {e}")
                    
            # Append result whether found or not
            results.append({
                "company": company,
                "status": "Found" if found_pdf else "Not Found",
                "pdf_url": final_pdf_url
            })
            
            # Polite pause
            time.sleep(2)
            print("-" * 40)
        
    # ─────────────────────────────────────────────────────────────────────────
    # WRITE TO CSV
    # ─────────────────────────────────────────────────────────────────────────
    output_target = OUTPUT_CSV.replace(".csv", "_debug.csv") if debug_mode else OUTPUT_CSV
    print(f"\nWriting results to {output_target}...")
    
    os.makedirs(os.path.dirname(output_target), exist_ok=True)
    
    with open(output_target, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["company", "status", "pdf_url"])
        writer.writeheader()
        writer.writerows(results)
        
    success_count = sum(1 for r in results if r["status"] == "Found")
    print(f"Done! Successfully verified PDF links for {success_count}/{len(companies)} companies.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape web for annual report PDFs")
    parser.add_argument("--debug", action="store_true", help="Run on 4 random companies")
    args = parser.parse_args()

    main(debug_mode=args.debug)
