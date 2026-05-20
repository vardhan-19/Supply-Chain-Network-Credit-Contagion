"""
append_group_b.py - Append Group B companies to company_financials_validated.csv
Also handles imputing subsidiary/brand companies from their parent row.
"""
import csv

CSV_PATH = r'd:\Supply Chain Network Credit Contagion\data\raw\company_financials_validated.csv'

# Read existing fieldnames
with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    existing_rows = list(reader)

# Build lookup for parent imputation
company_lookup = {}
for row in existing_rows:
    company_lookup[row['company_name'].strip()] = row

# ─── Group B rows to append ───
# Each tuple: (company_name, ticker, revenue, total_debt, market_cap, current_ratio,
#               debt_to_equity, profit_margin, revenue_growth, interest_coverage, roa,
#               data_confidence, year, source, parent_company, is_subsidiary, imputation_method)

new_rows = []

def make_row(name, ticker, revenue, total_debt, market_cap, current_ratio,
             debt_to_equity, profit_margin, revenue_growth, interest_coverage, roa,
             data_confidence, source, parent_company='', is_subsidiary='False', imputation_method='none'):
    return {
        'company_name': name, 'ticker': ticker,
        'revenue': str(revenue) if revenue else '',
        'total_debt': str(total_debt) if total_debt else '',
        'market_cap': str(market_cap) if market_cap else '',
        'current_ratio': str(current_ratio) if current_ratio else '',
        'debt_to_equity': str(debt_to_equity) if debt_to_equity else '',
        'profit_margin': str(profit_margin) if profit_margin else '',
        'revenue_growth': str(revenue_growth) if revenue_growth else '',
        'interest_coverage': str(interest_coverage) if interest_coverage else '',
        'roa': str(roa) if roa else '',
        'data_confidence': data_confidence,
        'year': '2025',
        'source': source,
        'parent_company': parent_company,
        'is_subsidiary': is_subsidiary,
        'imputation_method': imputation_method,
    }

def impute_from_parent(name, parent_name, source_note):
    """Create a row by copying financial data from an existing parent row."""
    parent = company_lookup.get(parent_name)
    if parent:
        row = make_row(
            name=name, ticker='',
            revenue=parent.get('revenue',''),
            total_debt=parent.get('total_debt',''),
            market_cap=parent.get('market_cap',''),
            current_ratio=parent.get('current_ratio',''),
            debt_to_equity=parent.get('debt_to_equity',''),
            profit_margin=parent.get('profit_margin',''),
            revenue_growth=parent.get('revenue_growth',''),
            interest_coverage=parent.get('interest_coverage',''),
            roa=parent.get('roa',''),
            data_confidence='imputed',
            source=source_note,
            parent_company=parent_name,
            is_subsidiary='True',
            imputation_method='parent_financials',
        )
        return row
    else:
        print(f"  WARN: Parent '{parent_name}' not found for {name}")
        return make_row(name, '', '', '', '', '', '', '', '', '', '', 'nan_fallback',
                       source_note, parent_name, 'True', 'parent_not_found')

# ─── CHUNK 1: Major private/missing companies ───

# Robert Bosch (private, no ticker)
new_rows.append(make_row(
    'Robert Bosch', '', 91000000000.0, '', '', '', '', 0.02, 0.008, '', '',
    'medium', 'Robert Bosch GmbH FY2025 Preliminary Results (bosch-press.com); revenue 91B EUR; EBIT margin ~2%; private company; no market cap/debt publicly disclosed'))

# ZF Friedrichshafen (private)
new_rows.append(make_row(
    'ZF Friedrichshafen', '', 38800000000.0, 10200000000.0, '', '', '', 0.045, -0.063, '', '',
    'medium', 'ZF Friedrichshafen FY2025 Annual Report (zf.com); revenue 38.8B EUR; adj EBIT margin 4.5%; net debt 10.2B EUR; net loss 2.1B EUR (one-time charges); private company'))

# Mahle GmbH (private)
new_rows.append(make_row(
    'Mahle GmbH', '', 11300000000.0, 3000000000.0, '', '', '', 0.02, -0.034, '', '',
    'medium', 'Mahle GmbH FY2025 LTM Sep 2025 (mahle.com); revenue ~11.3B EUR; adj debt 3.0B EUR; EBIT margin ~2%; Ba2 Moody rating; private company'))

# Yazaki (private Japanese)
new_rows.append(make_row(
    'Yazaki', '', 2492600000000.0, '', '', '', '', '', '', '', '',
    'low', 'Yazaki Corporation FY2024 (ending Jun 20 2024) corporate profile (yazaki-group.com); consolidated sales JPY 2.493T; private company; limited financial disclosure'))

# Marelli Holdings (Ch.11 bankruptcy)
new_rows.append(make_row(
    'Marelli', '', 11600000000.0, 4500000000.0, '', '', '', '', '', '', '',
    'medium', 'Marelli Holdings FY2025 (Ch.11 bankruptcy filed Jun 2025); gross revenue $11.6B; total debt ~$4.5B; DIP financing $1.1B; source: economictimes.com; marelli.com; spglobal.com'))

# SK On (subsidiary of SK Innovation) - impute from parent concept but with specific data
new_rows.append(make_row(
    'SK On', '', '', '', '', '', '', '', '', '', '',
    'nan_fallback', 'SK On is EV battery subsidiary of SK Innovation (096770.KS); merged with SK Enmove Nov 2025; operating loss narrowing; Q2 2025 battery revenue 2.1T KRW; targeting net profit surplus by 2026; source: alphaspread.com; askinno.com',
    'SK Innovation', 'True', 'parent_financials'))

# Hitachi Astemo (now Astemo Ltd)
new_rows.append(make_row(
    'Hitachi Astemo', '', 2186500000000.0, '', '', '', '', 0.031, '', '', '',
    'medium', 'Astemo Ltd (formerly Hitachi Astemo) FY2024 (ending Mar 2025); revenue JPY 2.187T; operating income JPY 67.4B (3.1% margin); renamed Astemo Ltd Apr 2025; source: astemo.com; hitachi.com'))

# Magna Steyr (division of Magna International) - impute from parent
new_rows.append(impute_from_parent(
    'Magna Steyr', 'Magna International',
    'Magna Steyr is contract manufacturing division of Magna International (MGA); complete vehicles segment declined 10% in 2025; source: magna.com FY2025 Annual Report'))

# ─── CHUNK 2: VW/BMW/Stellantis sub-brands + others ───

# Lamborghini (subsidiary of Audi/VW Group)
new_rows.append(make_row(
    'Lamborghini', '', 3197000000.0, '', '', '', '', 0.24, '', '', '',
    'medium', 'Automobili Lamborghini FY2025; revenue 3.197B EUR; op profit 768M EUR (24.0% margin); 10747 vehicles delivered; subsidiary of Audi AG/VW Group; source: audi-mediacenter.com; volkswagen-group.com',
    'Volkswagen Group', 'True', 'segment_reported'))

# Maserati (Stellantis brand) - impute
new_rows.append(impute_from_parent(
    'Maserati', 'Stellantis',
    'Maserati is luxury brand within Stellantis NV (STLA); no standalone public financials; Stellantis FY2025: revenue 153.5B EUR; source: stellantis.com'))

# Skoda Auto (VW Group brand) - impute
new_rows.append(impute_from_parent(
    'Skoda Auto', 'Volkswagen Group',
    'Skoda Auto is brand within Volkswagen Group (VWAGY); financials consolidated within VW Group FY2025 (321.9B EUR revenue); source: volkswagen-group.com'))

# Scania (Traton Group / VW Group)
new_rows.append(impute_from_parent(
    'Scania', 'Volkswagen Group',
    'Scania is subsidiary of Traton Group (part of Volkswagen Group); commercial vehicles; financials consolidated within VW Group; source: volkswagen-group.com FY2025'))

# MG Motor (SAIC Motor brand)
new_rows.append(impute_from_parent(
    'MG Motor', 'SAIC Motor',
    'MG Motor is brand owned by SAIC Motor (600104.SS); financials consolidated in SAIC Motor; source: saicmotor.com'))

# Rolls-Royce Motor Cars (BMW Group subsidiary)
new_rows.append(impute_from_parent(
    'Rolls-Royce Motor Cars', 'BMW Group',
    'Rolls-Royce Motor Cars is wholly-owned subsidiary of BMW Group (BMWYY); not same as Rolls-Royce Holdings plc (aerospace); financials in BMW Group; source: bmwgroup.com'))

# Mini (BMW Group brand)
new_rows.append(impute_from_parent(
    'Mini', 'BMW Group',
    'Mini is brand within BMW Group (BMWYY); financials consolidated within BMW Group annual report; source: bmwgroup.com'))

# ─── CHUNK 3: More brands and small entities ───

# Mercedes-AMG (Mercedes-Benz sub-brand)
new_rows.append(impute_from_parent(
    'Mercedes-AMG', 'Mercedes-Benz',
    'Mercedes-AMG is performance division of Mercedes-Benz Group (MBGAF); financials consolidated within Mercedes-Benz; source: mercedes-benz.com FY2025'))

# Mercedes-Maybach (Mercedes sub-brand)
new_rows.append(impute_from_parent(
    'Mercedes-Maybach', 'Mercedes-Benz',
    'Mercedes-Maybach is ultra-luxury sub-brand of Mercedes-Benz Group (MBGAF); financials consolidated within Mercedes-Benz; source: mercedes-benz.com'))

# Opel (Stellantis brand)
new_rows.append(impute_from_parent(
    'Opel', 'Stellantis',
    'Opel is brand within Stellantis NV (STLA); financials consolidated within Stellantis FY2025; source: stellantis.com'))

# Vauxhall (Stellantis brand, UK)
new_rows.append(impute_from_parent(
    'Vauxhall', 'Stellantis',
    'Vauxhall is UK brand within Stellantis NV (STLA); sister brand to Opel; financials in Stellantis FY2025; source: stellantis.com'))

# Jeep (Stellantis brand)
new_rows.append(impute_from_parent(
    'Jeep', 'Stellantis',
    'Jeep is brand within Stellantis NV (STLA); financials consolidated within Stellantis FY2025; source: stellantis.com'))

# Ram Trucks (Stellantis brand)
new_rows.append(impute_from_parent(
    'Ram Trucks', 'Stellantis',
    'Ram Trucks is brand within Stellantis NV (STLA); financials consolidated within Stellantis FY2025; source: stellantis.com'))

# Ioniq (Hyundai brand)
new_rows.append(impute_from_parent(
    'Ioniq', 'Hyundai Motor',
    'Ioniq is EV sub-brand of Hyundai Motor Group (HYMTF); financials consolidated within Hyundai Motor; source: hyundai.com'))

# UzAuto (Uzbekistan state-owned)
new_rows.append(make_row(
    'UzAuto', '', '', '', '', '', '', '', '', '', '',
    'nan_fallback', 'UzAuto Motors (formerly GM Uzbekistan) is state-owned Uzbek automaker; limited public financial data available; manufactures Chevrolet-branded vehicles under license'))

# ─── CHUNK 4: Divisions and subsidiaries ───

# Honda Financial Services (Ford-style captive finance)
new_rows.append(impute_from_parent(
    'Honda Financial Services', 'Honda Motor',
    'Honda Financial Services is captive financing subsidiary of Honda Motor (HMC); financials consolidated within Honda Motor annual report; source: honda.com'))

# NXP USA Inc (subsidiary of NXP Semiconductors)
new_rows.append(impute_from_parent(
    'NXP USA Inc', 'NXP Semiconductors',
    'NXP USA Inc is US operating subsidiary of NXP Semiconductors (NXPI); financials consolidated within NXP; source: nxp.com FY2025'))

# Novelis (subsidiary of Hindalco Industries)
new_rows.append(make_row(
    'Novelis', '', 17100000000.0, 5100000000.0, '', '', '', 0.04, '', '', '',
    'medium', 'Novelis Inc (subsidiary of Hindalco Industries); FY2024/25 revenue ~$17.1B; world largest aluminum rolling company; IPO filed 2024; source: novelis.com; hindalco.com annual report'))

# Nucor Tubular Products (division of Nucor)
new_rows.append(impute_from_parent(
    'Nucor Tubular Products', 'Nucor Steel',
    'Nucor Tubular Products is division of Nucor Corporation (NUE); financials consolidated within Nucor FY2025 ($32.5B revenue); source: nucor.com'))

# Lear Seating (division of Lear Corporation)
new_rows.append(impute_from_parent(
    'Lear Seating', 'Lear Corporation',
    'Lear Seating is Seating segment of Lear Corporation (LEA); financials consolidated within Lear FY2025; source: lear.com'))

# Steel Technologies (subsidiary of Nucor)
new_rows.append(impute_from_parent(
    'Steel Technologies', 'Nucor Steel',
    'Steel Technologies is processing subsidiary of Nucor Corporation (NUE); acquired by Nucor; financials in Nucor FY2025; source: nucor.com'))

# ZF Active Safety (division of ZF Friedrichshafen)
new_rows.append(make_row(
    'ZF Active Safety', '', '', '', '', '', '', '', '', '', '',
    'nan_fallback', 'ZF Active Safety is division of ZF Friedrichshafen AG; ADAS/autonomous driving division; financials in ZF Group FY2025 (38.8B EUR); source: zf.com',
    'ZF Friedrichshafen', 'True', 'parent_in_group_b'))

# Tenaciou3 Prospect Investment Limited
new_rows.append(make_row(
    'Tenaciou3 Prospect Investment Limited', '', '', '', '', '', '', '', '', '', '',
    'nan_fallback', 'Tenaciou3 Prospect Investment Limited is a BVI-registered investment holding entity; shareholder of BYD; no standalone operational financials; ownership/investment entity only'))

# Jaguar Land Rover (Tata Motors subsidiary)
new_rows.append(make_row(
    'Jaguar Land Rover', '', 29000000000.0, 6500000000.0, '', '', '', 0.06, 0.08, '', '',
    'medium', 'Jaguar Land Rover Automotive plc FY2024/25 (ending Mar 2025); est. revenue ~29B GBP; subsidiary of Tata Motors; source: jaguarlandrover.com; tatamotors.com annual report',
    'Tata Motors', 'True', 'segment_reported'))

# ─── Check for Guoxuan High-Tech (already in CSV from entries 101-150) ───
# Verified: Guoxuan High-Tech is already present in the validated CSV (entry 102)

# Append rows
with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    for row in new_rows:
        writer.writerow(row)

print(f"Appended {len(new_rows)} new rows to company_financials_validated.csv")
