import os
import networkx as nx
import pandas as pd
from graph.build_graph import build_graph
from graph.network_metrics import compute_topological_metrics

def test_build_graph():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    edges_csv = os.path.join(base_dir, "data", "processed", "edge_features_W.csv")
    
    G = build_graph(edges_csv)
    assert isinstance(G, nx.DiGraph)
    assert G.number_of_nodes() > 0
    assert G.number_of_edges() > 0

def test_topological_metrics_computation():
    G = nx.DiGraph()
    G.add_edge("comp_A", "comp_B", relationship_type="supply", confidence=1.0)
    G.add_edge("comp_B", "comp_C", relationship_type="supply", confidence=1.0)
    G.add_edge("comp_C", "comp_A", relationship_type="supply", confidence=1.0)

    metrics_df = compute_topological_metrics(G)
    assert isinstance(metrics_df, pd.DataFrame)
    assert len(metrics_df) == 3
    for col in [
        "entity_id",
        "in_degree",
        "out_degree",
        "betweenness_centrality",
        "eigenvector_centrality",
        "pagerank",
        "clustering_coefficient"
    ]:
        assert col in metrics_df.columns
