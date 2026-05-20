import csv

# Get all company names from supply_chain_combined.csv
sc_companies = set()
sc_edges = {}  # company -> list of (source_or_target, partner, rel_type)
with open(r'd:\Supply Chain Network Credit Contagion\data\raw\supply_chain_combined.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        s = row['source'].strip()
        t = row['target'].strip()
        rt = row['relationship_type'].strip()
        sc_companies.add(s)
        sc_companies.add(t)
        sc_edges.setdefault(s, []).append(('source', t, rt))
        sc_edges.setdefault(t, []).append(('target', s, rt))

# Get all companies from company_financials_validated.csv
fin_companies = {}
with open(r'd:\Supply Chain Network Credit Contagion\data\raw\company_financials_validated.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['company_name'].strip()
        fin_companies[name] = {
            'ticker': row.get('ticker','').strip(),
            'revenue': row.get('revenue','').strip(),
            'data_confidence': row.get('data_confidence','').strip(),
        }

# Group A: In financials but nan_fallback with no revenue (subsidiaries)
group_a = []
for c in sorted(sc_companies):
    if c in fin_companies:
        d = fin_companies[c]
        if d['data_confidence'] in ['nan_fallback', ''] and not d['revenue']:
            edges = sc_edges.get(c, [])
            group_a.append((c, d['ticker'], len(edges)))

# Group B: In SC edges but NOT in financials CSV at all
group_b = []
for c in sorted(sc_companies):
    if c not in fin_companies:
        edges = sc_edges.get(c, [])
        group_b.append((c, len(edges)))

print("=" * 70)
print("GROUP A: nan_fallback (subsidiaries to impute from parent)")
print("=" * 70)
for name, ticker, edge_count in group_a:
    tk = ticker if ticker else "no-ticker"
    print("  [" + tk + "] " + name + " (" + str(edge_count) + " edges)")

print()
print("=" * 70)
print("GROUP B: NOT in financials CSV at all (need research)")
print("=" * 70)
for name, edge_count in group_b:
    print("  " + name + " (" + str(edge_count) + " edges)")

print()
print("Group A count:", len(group_a))
print("Group B count:", len(group_b))
