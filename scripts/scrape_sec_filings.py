# -*- coding: utf-8 -*-
"""
SEC EDGAR 10-K Supplier Extraction Script (NLP Enhanced)
=========================================================
Phase 2: Supply Chain Credit Contagion Project

PURPOSE:
  Fetch up to 5 years of 10-K/20-F filings from SEC EDGAR for ALL anchor companies.
  Extract supplier-customer relationships using keyword proximity + spaCy NLP for
  Named Entity Recognition (NER), making it independent of LLM API costs.
  Appends unique edges to data/raw/supply_chain.csv aiming for 150+ edges.

PREREQUISITES:
  pip install requests beautifulsoup4 spacy
  python -m spacy download en_core_web_sm

HOW TO RUN:
  # Test mode (1 company, fast test)
  python scripts/scrape_sec_filings.py --test

  # Full run (all companies, max historical depth)
  python scripts/scrape_sec_filings.py
"""

import sys
# Must be first — sets encoding before any print() calls on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
import re
import csv
import time
import argparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

try:
    import spacy
    # Load small English model for Named Entity Recognition (NER)
    nlp = spacy.load("en_core_web_sm")
    print("✓ spaCy NLP model 'en_core_web_sm' loaded successfully.")
except ImportError:
    print("❌ ERROR: spaCy is not installed.")
    print("Please run: pip install spacy")
    print("And then:   python -m spacy download en_core_web_sm")
    sys.exit(1)
except OSError:
    print("❌ ERROR: spaCy model 'en_core_web_sm' not found.")
    print("Please run: python -m spacy download en_core_web_sm")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# SEC EDGAR policy: every automated request must include a descriptive User-Agent
SEC_HEADERS = {
    "User-Agent": "SupplyChainCreditContagion research@scncc-project.edu",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, text/html",
}

OUTPUT_CSV = r"D:\Supply Chain Network Credit Contagion\data\raw\supply_chain.csv"
REQUEST_DELAY_SEC = 0.25 # Polite delay (max 10 req/s on SEC)
CONTEXT_RADIUS = 600     # Chars to capture around keyword
MAX_FILINGS_PER_CO = 5   # Fetch up to 5 years of 10-K/20-F to maximize edge count

# ─────────────────────────────────────────────────────────────────────────────
# REQUESTS SESSION
# ─────────────────────────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=4, backoff_factor=0.5,
        status_forcelist=[403, 429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.headers.update(SEC_HEADERS)
    return session

SESSION = make_session()

# ─────────────────────────────────────────────────────────────────────────────
# TICKER TO CIK MAPPING (Dynamic Fallback)
# ─────────────────────────────────────────────────────────────────────────────
def get_sec_ticker_map():
    """Fetches official SEC mapping from Ticker to CIK."""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = SESSION.get(url, timeout=10)
        data = resp.json()
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for k, v in data.items()}
    except Exception as e:
        print(f"Warning: Could not fetch SEC ticker map: {e}")
        return {}

SEC_TICKER_MAP = get_sec_ticker_map()

# ─────────────────────────────────────────────────────────────────────────────
# ALL ANCHOR COMPANIES
# Replicating data/raw/anchor_companies.csv directly here per instruction.
# Note: For foreign or private companies that don't file SEC 10-K/20-F, we
# will attempt lookup. If SEC returns no filings, we safely skip.
# ─────────────────────────────────────────────────────────────────────────────
ANCHOR_COMPANIES = [
    {"name": "Toyota Motor",        "ticker": "TM",     "ftype": "20-F", "cik": "1094517"},
    {"name": "Volkswagen Group",    "ticker": "VWAGY",  "ftype": "20-F", "cik": ""},  # OTC, might not have EDGAR
    {"name": "General Motors",      "ticker": "GM",     "ftype": "10-K", "cik": "1467858"},
    {"name": "Ford Motor",          "ticker": "F",      "ftype": "10-K", "cik": "37996"},
    {"name": "Stellantis",          "ticker": "STLA",   "ftype": "20-F", "cik": "1605484"}, # formerly Fiat Chrysler
    {"name": "Honda Motor",         "ticker": "HMC",    "ftype": "20-F", "cik": "771806"},
    {"name": "BMW Group",           "ticker": "BMWYY",  "ftype": "20-F", "cik": ""},
    {"name": "Hyundai Motor",       "ticker": "HYMTF",  "ftype": "20-F", "cik": ""},
    {"name": "Tesla",               "ticker": "TSLA",   "ftype": "10-K", "cik": "1318605"},
    {"name": "Nissan Motor",        "ticker": "NSANY",  "ftype": "20-F", "cik": "1138118"},
    
    {"name": "Robert Bosch",        "ticker": "Private","ftype": "10-K", "cik": ""},
    {"name": "Denso Corp",          "ticker": "DNZOY",  "ftype": "20-F", "cik": ""},
    {"name": "ZF Friedrichshafen",  "ticker": "Private","ftype": "10-K", "cik": ""},
    {"name": "Magna International", "ticker": "MGA",    "ftype": "40-F", "cik": "749098"}, # Canadian filers use 40-F
    {"name": "Continental AG",      "ticker": "CTTAY",  "ftype": "20-F", "cik": ""},
    {"name": "Aisin Corp",          "ticker": "ASEKY",  "ftype": "20-F", "cik": ""},
    {"name": "Lear Corporation",    "ticker": "LEA",    "ftype": "10-K", "cik": "842162"},
    {"name": "Aptiv",               "ticker": "APTV",   "ftype": "10-K", "cik": "1521332"},
    {"name": "BorgWarner",          "ticker": "BWA",    "ftype": "10-K", "cik": "908255"},
    {"name": "Yazaki",              "ticker": "Private","ftype": "10-K", "cik": ""},
    {"name": "Hyundai Mobis",       "ticker": "HYUMY",  "ftype": "20-F", "cik": ""},
    {"name": "Faurecia / Forvia",   "ticker": "FURCF",  "ftype": "20-F", "cik": ""},
    
    {"name": "CATL",                "ticker": "300750", "ftype": "20-F", "cik": ""},
    {"name": "Panasonic Holdings",  "ticker": "PCRFY",  "ftype": "20-F", "cik": "1043273"},
    {"name": "Nucor Steel",         "ticker": "NUE",    "ftype": "10-K", "cik": "73309"},
    {"name": "Alcoa Corp",          "ticker": "AA",     "ftype": "10-K", "cik": "1675149"},
    {"name": "TSMC",                "ticker": "TSM",    "ftype": "20-F", "cik": "1046179"},
    {"name": "NXP Semiconductors",  "ticker": "NXPI",   "ftype": "20-F", "cik": "1413447"},
    {"name": "Flex Ltd",            "ticker": "FLEX",   "ftype": "10-K", "cik": "866374"},
    {"name": "BASF",                "ticker": "BASFY",  "ftype": "20-F", "cik": "1114532"}
]

# ─────────────────────────────────────────────────────────────────────────────
# KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────
SUPPLY_KEYWORDS = [
    "major supplier", "significant supplier", "key supplier",
    "sole source", "sole-source", "single source", "sole supplier",
    "supply agreement", "purchase from", "procure from",
    "raw material", "principal supplier", "primary supplier",
    "manufactured by", "provided by", "supplies us", "our supplier",
    "sourced from", "purchased from", "supply chain", "sources its",
    "relies on", "dependent on", "supplier concentration",
]

CUSTOMER_KEYWORDS = [
    "major customer", "significant customer", "key customer",
    "principal customer", "largest customer", "primary customer",
    "accounts for approximately", "represents approximately",
    "our customer", "sold to", "customer concentration",
]

ALL_KEYWORDS = SUPPLY_KEYWORDS + CUSTOMER_KEYWORDS

# Standardize NLP extraction filtering
IGNORED_NLP_ORGS = {
    "The Company", "Company", "SEC", "FASB", "COVID-19", "US", "U.S.", 
    "Tax", "Board of Directors", "Board", "Congress", "EPA", "NHTSA",
    "State", "Federal", "Government", "European Union", "EU", "GAAP",
    "Management", "Stock Exchange", "NYSE", "NASDAQ", "LLC", "Inc.",
    "Corp.", "Ltd.", "Group"
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Get all desired filings for a CIK natively
# ─────────────────────────────────────────────────────────────────────────────
def get_filings_metadata(cik: str, form_type: str, max_filings: int = MAX_FILINGS_PER_CO) -> list:
    """
    Fetch up to `max_filings` history for the requested form type (10-K, 20-F, 40-F)
    so we can extract older relationships and multiply our edge count.
    """
    cik_padded = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    
    filings = []
    try:
        resp = SESSION.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        recent = data.get("filings", {}).get("recent", {})
        forms    = recent.get("form", [])
        accnos   = recent.get("accessionNumber", [])
        rptdates = recent.get("reportDate", [])
        prim_doc = recent.get("primaryDocument", [])
        
        for i, form in enumerate(forms):
            # Also allow 10-K/A or 20-F/A (amendments)
            if form_type in form and prim_doc[i]:
                acc_nodash = accnos[i].replace("-", "")
                year = rptdates[i][:4] if rptdates[i] else "UnknownYear"
                
                filings.append({
                    "accession":   accnos[i],
                    "acc_nodash":  acc_nodash,
                    "report_date": rptdates[i],
                    "year":        year,
                    "primary_doc": prim_doc[i],
                    "cik_int":     int(cik)
                })
                if len(filings) >= max_filings:
                    break
                    
    except Exception as exc:
        print(f"    [ERROR] Submissions API failed: {exc}")
        
    return filings

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Download & Extract Context Snippets
# ─────────────────────────────────────────────────────────────────────────────
def fetch_and_extract_snippets(cik_int: int, acc_nodash: str, primary_doc: str) -> list:
    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{primary_doc}"
    
    try:
        resp = SESSION.get(doc_url, timeout=90)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "head", "footer", "nav", "table"]): 
            # Drop tables to reduce noise: relationships are usually in prose sentences.
            tag.decompose()
            
        full_text = soup.get_text(separator=" ", strip=True)
        full_text = re.sub(r"\s+", " ", full_text)
        
        snippets = []
        text_lower = full_text.lower()
        
        for keyword in ALL_KEYWORDS:
            start_pos = 0
            while True:
                pos = text_lower.find(keyword, start_pos)
                if pos == -1: break
                
                ctx_start = max(0, pos - CONTEXT_RADIUS)
                ctx_end   = min(len(full_text), pos + len(keyword) + CONTEXT_RADIUS)
                snippet   = full_text[ctx_start:ctx_end]
                
                snippets.append((keyword, snippet))
                start_pos = pos + 1
                
        return snippets
        
    except Exception as exc:
        print(f"    [ERROR] Fetching document failed: {exc}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# NLP NLP NLP: Extract relationships dynamically via spaCy ORG NER
# ─────────────────────────────────────────────────────────────────────────────
def extract_relationships_nlp(snippets: list, filing_company: str, source_tag: str, year: str) -> list:
    """
    Independent NLP Logic: No LLM/GPT used.
    Uses spaCy Named Entity Recognition to find 'ORG' (organizations).
    Matches them to contextual keywords.
    """
    relationships = []
    seen_pairs = set()

    for keyword, snippet in snippets:
        if not snippet.strip(): continue
        
        snippet_lower = snippet.lower()
        is_supply_kw   = keyword in SUPPLY_KEYWORDS
        is_customer_kw = keyword in CUSTOMER_KEYWORDS
        
        # Run spaCy NLP on the snippet
        doc = nlp(snippet)
        
        # Extract all Organizations (ORG) identified by spaCy
        orgs_found = set()
        for ent in doc.ents:
            if ent.label_ == "ORG":
                # Clean up the name
                org_name = ent.text.replace("\n", " ").strip()
                # Filter out generic words
                if len(org_name) > 3 and org_name not in IGNORED_NLP_ORGS:
                    # Make sure it's not basically just the filing company name
                    if filing_company.split()[0].lower() not in org_name.lower():
                        orgs_found.add(org_name)
        
        # Assign relationships
        for org in orgs_found:
            # Determine direction of edge
            if is_supply_kw and not is_customer_kw:
                supplier = org
                customer = filing_company
                rel_type = "tier1_supplier"
                confidence = 0.70 # Moderated confidence for pure NLP NER
                
                if any(m in snippet_lower for m in ["battery", "cell", "lithium"]):
                    rel_type = "tier2_supplier_battery"
                elif any(m in snippet_lower for m in ["semiconductor", "chip", "microcontroller"]):
                    rel_type = "tier2_supplier_semiconductor"
                elif any(m in snippet_lower for m in ["steel", "aluminum", "raw material"]):
                    rel_type = "raw_material_supplier"
                    
            elif is_customer_kw and not is_supply_kw:
                supplier = filing_company
                customer = org
                rel_type = "tier1_supplier"
                confidence = 0.65
                
            else:
                continue

            # Deduplicate locally
            pair_key = (supplier, customer, year)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            
            note_clean = snippet.strip()[:150].replace("\n", " ")

            relationships.append({
                "supplier":          supplier,
                "customer":          customer,
                "relationship_type": rel_type,
                "data_source":       source_tag,
                "confidence":        confidence,
                "year":              year,
                "notes":             f"[NLP:{keyword}] {note_clean}"
            })

    return relationships

# ─────────────────────────────────────────────────────────────────────────────
# WRITE TO CSV (Preserving existing, Append unique only)
# ─────────────────────────────────────────────────────────────────────────────
def write_csv(new_relationships: list, output_path: str):
    FIELDNAMES = ["supplier", "customer", "relationship_type",
                  "data_source", "confidence", "year", "notes"]

    existing_rows = []
    # Deduplicate strictly on (supplier, customer) disregarding year to avoid duplicates per edge
    existing_pairs = set()

    if os.path.exists(output_path):
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "supplier_name" in row:
                    row["supplier"] = row.pop("supplier_name", "")
                    row["customer"] = row.pop("customer_name", "")
                    row.setdefault("year", "2024")
                    row.setdefault("notes", "manual_stub")
                    
                supplier = row.get("supplier", "").lower().strip()
                customer = row.get("customer", "").lower().strip()
                existing_rows.append(row)
                existing_pairs.add((supplier, customer))

    truly_new = []
    for r in new_relationships:
        sup_norm = r["supplier"].lower().strip()
        cust_norm = r["customer"].lower().strip()
        if (sup_norm, cust_norm) not in existing_pairs:
            truly_new.append(r)
            existing_pairs.add((sup_norm, cust_norm))

    all_rows = existing_rows + truly_new

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n  CSV written: {len(all_rows)} total edges "
          f"({len(truly_new)} newly appended, {len(existing_rows)} preserved)")
    return len(truly_new)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE 
# ─────────────────────────────────────────────────────────────────────────────
def main(test_mode: bool = False):
    print("=" * 70)
    print("SEC EDGAR 10-K Supplier Extraction (NLP spaCy) | Phase 2, Step 2")
    if test_mode: print("*** TEST MODE: processing only General Motors ***")
    print("=" * 70)

    # Resolve missing CIKs statically using SEC map before loop
    for company in ANCHOR_COMPANIES:
        if not company.get("cik"):
            if company["ticker"] in SEC_TICKER_MAP:
                company["cik"] = SEC_TICKER_MAP[company["ticker"]]

    companies_to_run = [ANCHOR_COMPANIES[2]] if test_mode else ANCHOR_COMPANIES
    all_relationships = []

    for company in companies_to_run:
        name   = company["name"]
        cik    = company["cik"]
        ticker = company["ticker"]
        ftype  = company["ftype"]

        print(f"\n[{ticker}] {name}")
        
        if not cik:
            print(f"  [SKIP] No CIK available for {name} (Foreign/Private?)")
            continue

        time.sleep(REQUEST_DELAY_SEC)
        
        # Extract MULTIPLE historical filings (Max 5) to maximize edge count!
        filings = get_filings_metadata(cik, ftype, max_filings=MAX_FILINGS_PER_CO)
        
        if not filings:
            print(f"  [SKIP] No {ftype} filings found in EDGAR")
            continue

        for filing in filings:
            year       = filing["year"]
            source_tag = f"sec_{ftype.lower().replace('-','')}_{ticker}_{year}"
            print(f"  -> Filing : {filing['accession']} | Year: {year}")
            
            time.sleep(REQUEST_DELAY_SEC)
            snippets = fetch_and_extract_snippets(filing["cik_int"], filing["acc_nodash"], filing["primary_doc"])
            
            if not snippets:
                continue
                
            print(f"     Keyword snippets: {len(snippets)}")
            
            rels = extract_relationships_nlp(snippets, name, source_tag, year)
            print(f"     Edges extracted : {len(rels)}")
            
            all_relationships.extend(rels)

    print(f"\n{'=' * 70}")
    print(f"Total relationships extracted via NLP: {len(all_relationships)}")
    added = write_csv(all_relationships, OUTPUT_CSV)
    print(f"Done! Aiming for 150+ edges... Accumulated total edges in CSV now updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SEC EDGAR for suppliers (NLP)")
    parser.add_argument("--test", action="store_true", help="Run on only General Motors")
    args = parser.parse_args()

    main(test_mode=args.test)
