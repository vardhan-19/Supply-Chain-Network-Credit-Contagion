import sqlite3
import pandas as pd
import os
import math

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'scncc.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def clear_tables():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relationships")
        cursor.execute("DELETE FROM companies")
        conn.commit()
        print("Existing data cleared from tables.")
    except Exception as e:
        print(f"Error clearing tables: {e}")
    finally:
        conn.close()

def load_companies(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    # Map CSV columns to SQLite schema
    companies_data = []
    for _, row in df.iterrows():
        companies_data.append((
            row.get('entity_id'),
            row.get('company_name'),
            row.get('ticker') if pd.notna(row.get('ticker')) else None,
            None, # sector
            None, # tier
            None, # country
            None, # is_public
            row.get('revenue') if pd.notna(row.get('revenue')) else None,
            row.get('total_debt') if pd.notna(row.get('total_debt')) else None,
            row.get('market_cap') if pd.notna(row.get('market_cap')) else None,
            row.get('current_ratio') if pd.notna(row.get('current_ratio')) else None,
            row.get('debt_to_equity') if pd.notna(row.get('debt_to_equity')) else None,
            row.get('profit_margin') if pd.notna(row.get('profit_margin')) else None,
            row.get('revenue_growth') if pd.notna(row.get('revenue_growth')) else None,
            row.get('interest_coverage') if pd.notna(row.get('interest_coverage')) else None,
            row.get('roa') if pd.notna(row.get('roa')) else None,
            row.get('altman_z_score') if pd.notna(row.get('altman_z_score')) else None,
            int(row.get('default_label')) if pd.notna(row.get('default_label')) else 0
        ))

    conn = get_connection()
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO companies (
                id, name, ticker, sector, tier, country, is_public,
                revenue, total_debt, market_cap, current_ratio, debt_to_equity,
                profit_margin, revenue_growth, interest_coverage, roa,
                altman_z_score, default_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_query, companies_data)
        conn.commit()
        print(f"Successfully loaded {len(companies_data)} companies.")
    except Exception as e:
        print(f"Error loading companies: {e}")
    finally:
        conn.close()

def load_relationships(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    # Map CSV columns to SQLite schema
    relationships_data = []
    for _, row in df.iterrows():
        relationships_data.append((
            row.get('source_id'),
            row.get('target_id'),
            row.get('relationship_type') if pd.notna(row.get('relationship_type')) else None,
            1.0, # weight
            row.get('confidence') if pd.notna(row.get('confidence')) else 1.0,
            row.get('data_source') if pd.notna(row.get('data_source')) else None,
            int(row.get('year')) if pd.notna(row.get('year')) else None
        ))

    conn = get_connection()
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO relationships (
                supplier_id, customer_id, relationship_type, weight,
                confidence, data_source, year
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_query, relationships_data)
        conn.commit()
        print(f"Successfully loaded {len(relationships_data)} relationships.")
    except Exception as e:
        print(f"Error loading relationships: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    company_csv = r'd:\Supply Chain Network Credit Contagion\data\processed\company_financials_resolved.csv'
    relationship_csv = r'd:\Supply Chain Network Credit Contagion\data\processed\supply_chain_resolved.csv'
    
    print("Loading data...")
    clear_tables()
    load_companies(company_csv)
    load_relationships(relationship_csv)
    print("Data load complete.")
