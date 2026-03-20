"""
Quick diagnostic script to see what keyword-context snippets are being
extracted from the GM 10-K. Helps debug why company names are not being matched.
Prints the first 30 snippets and all company name matches found.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re, time, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

SEC_HEADERS = {
    "User-Agent": "SupplyChainCreditContagion research@scncc-project.edu",
    "Accept-Encoding": "gzip, deflate",
}

def make_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429,500,502,503,504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update(SEC_HEADERS)
    return s

SESSION = make_session()
CONTEXT_RADIUS = 600  # wider for diagnostics

SUPPLY_KEYWORDS = [
    "major supplier", "significant supplier", "key supplier",
    "sole source", "sole-source", "single source", "sole supplier",
    "supply agreement", "purchase from", "procure from",
    "raw material", "principal supplier", "primary supplier",
    "manufactured by", "provided by", "supplies us", "our supplier",
    "sourced from", "purchased from", "supply chain", "sources its",
    "relies on", "dependent on", "supplier concentration",
    "our suppliers", "key suppliers", "industry supplier",
    "direct material", "indirect material", "cost of material",
    "commodity", "steel", "aluminum", "lithium", "cobalt",
]

CUSTOMER_KEYWORDS = [
    "major customer", "significant customer", "key customer",
    "principal customer", "largest customer", "accounts for approximately",
    "represents approximately", "our customer", "sold to",
    "customer concentration", "significant revenue",
]

ALL_KEYWORDS = SUPPLY_KEYWORDS + CUSTOMER_KEYWORDS

# GM filing URL (already known from test run)
GM_URL = "https://www.sec.gov/Archives/edgar/data/1467858/000146785826000013/gm-20251231.htm"

print("Fetching GM 10-K...")
resp = SESSION.get(GM_URL, timeout=90)
soup = BeautifulSoup(resp.content, "html.parser")
for tag in soup(["script", "style", "head", "footer", "nav"]):
    tag.decompose()

full_text = soup.get_text(separator=" ", strip=True)
full_text = re.sub(r"\s+", " ", full_text)
print(f"Total text length: {len(full_text):,} characters")

# Find all keyword snippets
snippets = []
text_lower = full_text.lower()

for kw in ALL_KEYWORDS:
    pos = 0
    while True:
        idx = text_lower.find(kw, pos)
        if idx == -1:
            break
        start = max(0, idx - CONTEXT_RADIUS)
        end   = min(len(full_text), idx + len(kw) + CONTEXT_RADIUS)
        snippets.append((kw, full_text[start:end]))
        pos = idx + 1

print(f"Total keyword hits: {len(snippets)}")
print()

# Show first 25 unique snippets
print("=" * 80)
print("SAMPLE SNIPPETS (first 25):")
print("=" * 80)
seen_kw = {}
for kw, snippet in snippets:
    if seen_kw.get(kw, 0) >= 2:     # show max 2 per keyword
        continue
    seen_kw[kw] = seen_kw.get(kw, 0) + 1
    print(f"\n--- KEYWORD: '{kw}' ---")
    print(snippet[:400])
    print()
    if sum(seen_kw.values()) >= 25:
        break

# Now look for ANY proper-noun-like capitalized words in snippets
# to find company names we might be missing
print("\n" + "=" * 80)
print("CAPITALIZED PROPER NOUNS appearing near supply keywords:")
print("=" * 80)
all_cap_words = {}
for kw, snippet in snippets:
    if "supplier" not in kw and "supply" not in kw and "raw material" not in kw:
        continue
    # Find Title Case sequences (company name patterns)
    matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', snippet)
    for m in matches:
        if len(m) > 4 and m not in ("This", "The", "Our", "We", "In", "If",
                                     "For", "Upon", "With", "After", "Before",
                                     "During", "Each", "When", "Where", "While"):
            all_cap_words[m] = all_cap_words.get(m, 0) + 1

# Print top 50 most frequent proper nouns near supply keywords
print("Top proper nouns near supply keywords (by frequency):")
for word, count in sorted(all_cap_words.items(), key=lambda x: -x[1])[:60]:
    print(f"  {count:3d}x  {word}")
