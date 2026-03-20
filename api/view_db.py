import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'scncc.db')

def view_table(table_name):
    """
    Display the content of a specific table in the SQLite database.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        
        print(f"\n--- Table: {table_name} ---")
        if df.empty:
            print("(Table is currently empty)")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"Error viewing table {table_name}: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("SCNCC Database Viewer")
    view_table('companies')
    view_table('relationships')
