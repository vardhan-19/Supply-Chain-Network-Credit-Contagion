import sqlite3
import pandas as pd
import os

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'scncc.db')

def load_companies(csv_path):
    """
    Load processed company financials CSV into the companies table.
    """
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql('companies', conn, if_exists='append', index=False)
        print(f"Successfully loaded {len(df)} companies.")
    except Exception as e:
        print(f"Error loading companies: {e}")
    finally:
        conn.close()

def load_relationships(csv_path):
    """
    Load processed supply chain relationship CSV into the relationships table.
    """
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql('relationships', conn, if_exists='append', index=False)
        print(f"Successfully loaded {len(df)} relationships.")
    except Exception as e:
        print(f"Error loading relationships: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Placeholder for paths from processed data
    # company_csv = r'd:\Supply Chain Network Credit Contagion\data\processed\company_financials.csv'
    # relationship_csv = r'd:\Supply Chain Network Credit Contagion\data\processed\supply_chain.csv'
    
    # print("Loading data...")
    # load_companies(company_csv)
    # load_relationships(relationship_csv)
    print("load_data.py is ready. Uncomment path variables when processed CSVs are available.")
