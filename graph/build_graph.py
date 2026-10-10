import pandas as pd
import networkx as nx
import os

def build_graph(csv_path):
    """
    Constructs a NetworkX DiGraph from the automotive supply chain CSV data.
    
    Academic Foundations:
    - Multi-Relational Enterprise Graph: Liu (ACM AIDF 2025) formulation of automotive
      supply chain graphs spanning commercial supply flows, trade credit, and equity ownership.
    - Bilateral Trade Credit Exposure: Geng, Han, Yang, & Zhao (PLoS ONE 2024) modeling of
      accounts receivable exposure and transaction proportion weighting.
    """
    df = pd.read_csv(csv_path)
    
    # Initialize a directed graph
    G = nx.DiGraph()
    
    # Add edges with attributes
    for _, row in df.iterrows():
        source_id = row['source_id']
        target_id = row['target_id']
        
        edge_attrs = {
            'relationship_type': row['relationship_type'],
            'confidence': float(row['confidence']) if pd.notna(row['confidence']) else 1.0,
        }
        
        # Optional attributes based on data availability
        for col in ['payment_terms', 'credit_amount_usd', 'ownership_pct', 'equity_value_usd']:
            if col in df.columns and pd.notna(row[col]):
                edge_attrs[col] = row[col]
                
        G.add_edge(source_id, target_id, **edge_attrs)
        
    return G

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'processed', 'supply_chain_resolved.csv')
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
    else:
        G = build_graph(csv_path)
        print("Graph built successfully.")
        print(f"Number of nodes: {G.number_of_nodes()}")
        print(f"Number of edges: {G.number_of_edges()}")
