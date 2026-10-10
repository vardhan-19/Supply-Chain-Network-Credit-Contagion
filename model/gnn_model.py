import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class SupplyChainGNN(nn.Module):
    """
    2-Layer Graph Convolutional Network (GCN) with Edge-Weighted Message Passing.
    
    Academic Foundations:
    - Convolutional Architecture: Kipf & Welling (ICLR 2017) first-order Chebyshev
      spectral graph convolution approximation: D^{-1/2} A D^{-1/2} X W.
    - Automotive Supply Graph Message Passing: Liu (ACM AIDF 2025) collaborative
      risk perception where default probability is conditioned on counterparty topology.
    - Feature Space: Mojdehi, Amiri, & Haddadi (IEEE Access 2025) hybrid feature
      tensor combining 8 financial ratios with 4 topological centralities.
    - Edge Weighting: Continuous transmission weights with temporal decay (Geng et al., 2024).
    """
    def __init__(self, num_features: int):
        super(SupplyChainGNN, self).__init__()
        
        # Input Linear layer (num_features -> 64)
        self.lin_in = nn.Linear(num_features, 64)
        
        # First message passing layer (64 -> 64)
        self.conv1 = GCNConv(64, 64)
        
        # Dropout
        self.dropout = nn.Dropout(p=0.5)
        
        # Second message passing layer (64 -> 32)
        self.conv2 = GCNConv(64, 32)
        
        # Final Linear layer (32 -> 2)
        self.lin_out = nn.Linear(32, 2)
        
    def forward(self, x, edge_index, edge_attr=None):
        # Feature transformation
        x = self.lin_in(x)
        
        # First GNN layer + ReLU + Dropout
        # edge_attr contains edge weights w_ij; pass it to GCNConv
        # NOTE: w_ij=0 means zero contagion transmission — GCNConv treats this
        # as a removed edge during message passing, which is by design.
        x = self.conv1(x, edge_index, edge_weight=edge_attr.view(-1) if edge_attr is not None else None)
        x = F.relu(x)
        x = self.dropout(x)
        
        # Second GNN layer
        x = self.conv2(x, edge_index, edge_weight=edge_attr.view(-1) if edge_attr is not None else None)
        
        # Final classification layer
        out = self.lin_out(x)
        
        # Log softmax
        return F.log_softmax(out, dim=-1)

if __name__ == "__main__":
    try:
        # Validate instantiation
        test_num_features = 12
        model = SupplyChainGNN(num_features=test_num_features)
        print("SupplyChainGNN module instantiated successfully.")
        print(model)
    except Exception as e:
        print(f"Failed to instantiate SupplyChainGNN: {e}")
