"""
impute_subsidiaries.py
---------------------
Reads company_financials_validated.csv and imputes financials for subsidiary
companies from their parent company's row. Adds parent_company, is_subsidiary,
and imputation_method columns to ALL rows.

Usage: python data/impute_subsidiaries.py
"""
import csv
import os

# ─── Configuration: subsidiary → parent mapping ───
# Each key is the subsidiary company_name, value is the parent company_name
PARENT_MAP = {
    # Stellantis brands
    "Alfa Romeo":              "Stellantis",
    "Chrysler":                "Stellantis",
    "Citroen":                 "Stellantis",
    "Dodge":                   "Stellantis",
    "Fiat":                    "Stellantis",
    # BMW Group divisions
    "BMW Brilliance":          "BMW Group",
    "BMW Financial Services":  "BMW Group",
    # BorgWarner divisions
    "BorgWarner PowerDrive":   "BorgWarner",
    # Continental
    "Continental Automotive":  "Continental AG",
    # Denso
    "Denso Manufacturing":     "Denso Corp",
    # GM brands
    "Buick":                   "General Motors",
    "Cadillac":                "General Motors",
    "Chevrolet":               "General Motors",
    "GM Financial's":          "General Motors",
    # Renault brands
    "Dacia":                   "Renault Group",
    # Nissan brands
    "Infiniti":                "Nissan Motor",
    # Hyundai brands
    "Genesis Motors":          "Hyundai Motor",
    # VW Group / Audi sub-brands
    "Ducati":                  "Volkswagen Group",
    # Flex divisions
    "Flex Automotive":         "Flex Ltd",
    # Ford
    "Ford Motor Credit":       "Ford Motor",
    # Daihatsu
    "Daihatsu Motor":          "Toyota Motor",
    # Audi AG (already has partial data, impute missing from VW Group)
    "Audi AG":                 "Volkswagen Group",
    # Bentley (has partial data, impute missing from VW Group)
    "Bentley Motors":          "Volkswagen Group",
}

# These stay as nan_fallback (government/ownership entities or private JVs)
KEEP_NAN = {
    "French State", "BPIfrance", "Bugatti Rimac", "Envision AESC",
    "Boston Dynamics", "BASF Coatings", "Alcoa Fastening Systems",
}

# Columns that carry financial data (to be imputed from parent)
FINANCIAL_COLS = [
    'revenue', 'total_debt', 'market_cap', 'current_ratio',
    'debt_to_equity', 'profit_margin', 'revenue_growth',
    'interest_coverage', 'roa'
]

def main():
    csv_path = r'd:\Supply Chain Network Credit Contagion\data\raw\company_financials_validated.csv'

    # ─── Step 1: Read all rows ───
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # ─── Step 2: Build lookup by company name ───
    company_lookup = {}
    for i, row in enumerate(rows):
        company_lookup[row['company_name'].strip()] = i

    # ─── Step 3: Add new columns to fieldnames ───
    new_fieldnames = original_fieldnames + ['parent_company', 'is_subsidiary', 'imputation_method']

    # ─── Step 4: Process each row ───
    imputed_count = 0
    for row in rows:
        name = row['company_name'].strip()

        # Default values for new columns
        row['parent_company'] = ''
        row['is_subsidiary'] = 'False'
        row['imputation_method'] = 'none'

        if name in PARENT_MAP:
            parent_name = PARENT_MAP[name]
            row['parent_company'] = parent_name
            row['is_subsidiary'] = 'True'

            # Find parent row
            if parent_name in company_lookup:
                parent_row = rows[company_lookup[parent_name]]

                # Only impute if this row has no revenue (nan_fallback)
                if not row.get('revenue', '').strip():
                    for col in FINANCIAL_COLS:
                        if col in parent_row and parent_row[col].strip():
                            row[col] = parent_row[col]
                    row['imputation_method'] = 'parent_financials'
                    row['data_confidence'] = 'imputed'
                    imputed_count += 1
                    print(f"  IMPUTED: {name} <- {parent_name}")
                else:
                    # Has partial data — keep existing, just mark parent
                    row['imputation_method'] = 'partial_existing'
                    print(f"  PARTIAL: {name} (has data, parent={parent_name})")
            else:
                print(f"  WARN: Parent '{parent_name}' not found for {name}")

        elif name in KEEP_NAN:
            row['imputation_method'] = 'kept_nan_fallback'
            print(f"  KEPT NAN: {name}")

    # ─── Step 5: Write back ───
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Imputed {imputed_count} subsidiaries. File updated.")

if __name__ == '__main__':
    main()
