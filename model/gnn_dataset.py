import os
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data
from sklearn.preprocessing import StandardScaler

def build_dataset(nodes_csv: str, edges_csv: str) -> Data:
    """
    Loads nodes and edges CSVs, maps entity_id to contiguous indices,
    and returns a PyTorch Geometric Data object.
    """
    # Load CSVs
    df_nodes = pd.read_csv(nodes_csv)
    df_edges = pd.read_csv(edges_csv)
    
    # 1. Map entity_id to contiguous integer indices [0, N-1]
    unique_entities = df_nodes['entity_id'].unique()
    entity_to_idx = {entity_id: idx for idx, entity_id in enumerate(unique_entities)}
    
    # 2. Extract node features 'x'
    # Select numerical columns for features
    # Exclude columns that would cause data leakage or are redundant for the GNN:
    #   - default_label: target variable (y) — cannot be a feature
    #   - altman_z_score: directly determines default_label (Z ≤ 1.81 → label=1),
    #     using it as a feature would let the model memorize the threshold instead
    #     of learning genuine credit risk patterns from the supply chain network
    #   - year: same value (2025) for all rows — zero discriminative power
    #   - in_degree / out_degree: redundant — GNN learns degree information
    #     implicitly through its message-passing aggregation mechanism
    #   - interest_coverage: too many missing values across the dataset
    exclude_cols = ['default_label', 'altman_z_score', 'year', 'in_degree', 'out_degree', 'interest_coverage']
    numeric_cols = df_nodes.select_dtypes(include=['float64', 'int64']).columns
    feature_cols = [col for col in numeric_cols if col not in exclude_cols]
    
    x_df = df_nodes[feature_cols].fillna(0)
    
    # 3. Add train/test masks (80/20 split)
    num_nodes = x_df.shape[0]
    
    # Use a local RandomState to avoid polluting the global numpy RNG
    rng = np.random.RandomState(42)
    indices = rng.permutation(num_nodes)
    train_size = int(0.8 * num_nodes)
    
    train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    test_mask = torch.zeros(num_nodes, dtype=torch.bool)
    
    train_mask[indices[:train_size]] = True
    test_mask[indices[train_size:]] = True
    
    # 4. Scale features (Fit only on training data to prevent data leakage)
    scaler = StandardScaler()
    scaler.fit(x_df.values[indices[:train_size]])
    x_scaled = scaler.transform(x_df.values)
    x = torch.tensor(x_scaled, dtype=torch.float32)
    
    # 5. Extract labels 'y'
    y = torch.tensor(df_nodes['default_label'].values, dtype=torch.long)
    
    # 6. Build edge_index
    # Filter edges to only those where both source_id and target_id are in our mapping
    valid_edges = df_edges[
        df_edges['source_id'].isin(entity_to_idx) & 
        df_edges['target_id'].isin(entity_to_idx)
    ]
    
    source_indices = valid_edges['source_id'].map(entity_to_idx).values
    target_indices = valid_edges['target_id'].map(entity_to_idx).values
    
    edge_index = torch.tensor(np.array([source_indices, target_indices]), dtype=torch.long)
    
    # 7. Extract edge_attr (edge weights 'w_ij')
    edge_attr = valid_edges['w_ij'].fillna(0).values
    edge_attr = torch.tensor(edge_attr, dtype=torch.float32).view(-1, 1)
    
    # 8. Create PyG Data object
    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr, y=y)
    data.train_mask = train_mask
    data.test_mask = test_mask
    
    # Attach unscaled revenue for downstream EAD calculations in stress testing
    if 'revenue' in df_nodes.columns:
        raw_revenues = df_nodes['revenue'].fillna(0).values
        data.raw_revenue = torch.tensor(raw_revenues, dtype=torch.float32)

    # Attach entity mappings for node lookup
    data.entity_to_idx = entity_to_idx
    data.idx_to_entity = {idx: entity_id for entity_id, idx in entity_to_idx.items()}
    
    return data

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "node_features_X.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edge_features_W.csv")
    
    try:
        data = build_dataset(nodes_csv, edges_csv)
        print("Dataset instantiated successfully.")
        print(f"Data object: {data}")
        print(f"x shape: {data.x.shape}")
        print(f"edge_index shape: {data.edge_index.shape}")
        print(f"edge_attr shape: {data.edge_attr.shape}")
        print(f"y shape: {data.y.shape}")
    except Exception as e:
        print(f"Failed to build dataset: {e}")
