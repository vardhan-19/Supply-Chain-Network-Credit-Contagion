import networkx as nx
import pandas as pd

def compute_topological_metrics(G):
    """
    Computes structural risk metrics for every node in the graph based on their network position.
    Returns a pandas DataFrame keyed by entity_id.
    
    Academic Foundations:
    - Topological Risk Indicators: Mojdehi, Amiri, & Haddadi (IEEE Access 2025)
      demonstrated that integrating network topological centralities (Betweenness Centrality,
      Eigenvector Centrality, PageRank, Clustering Coefficient) with financial accounting
      ratios provides decisive predictive power for supply chain credit distress.
    """
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())
    
    # Betweenness centrality
    betweenness = nx.betweenness_centrality(G)
    
    # Eigenvector centrality (fallback to numpy if power iteration fails to converge)
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        eigenvector = nx.eigenvector_centrality_numpy(G)
        
    # PageRank
    pagerank = nx.pagerank(G)
    
    # Clustering coefficient (requires undirected graph)
    G_undirected = G.to_undirected()
    clustering = nx.clustering(G_undirected)
    
    # Compile into a list of dictionaries
    metrics = []
    for node in G.nodes():
        metrics.append({
            'entity_id': node,
            'in_degree': in_degree.get(node, 0),
            'out_degree': out_degree.get(node, 0),
            'betweenness_centrality': betweenness.get(node, 0.0),
            'eigenvector_centrality': eigenvector.get(node, 0.0),
            'pagerank': pagerank.get(node, 0.0),
            'clustering_coefficient': clustering.get(node, 0.0)
        })
        
    # Convert to DataFrame
    metrics_df = pd.DataFrame(metrics)
    return metrics_df

if __name__ == "__main__":
    # For independent testing
    import os
    import sys
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(base_dir)
    from graph.build_graph import build_graph
    
    csv_path = os.path.join(base_dir, 'data', 'processed', 'supply_chain_resolved.csv')
    G = build_graph(csv_path)
    df = compute_topological_metrics(G)
    print(df.head())
