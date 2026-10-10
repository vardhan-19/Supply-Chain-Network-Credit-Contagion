import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class SupplyChainGNN(nn.Module):
    """
    Two-layer Graph Convolutional Network (GCN) with edge-weighted message passing
    for supply chain credit contagion and default risk estimation.
    """
    def __init__(self, num_features: int):
        super(SupplyChainGNN, self).__init__()
        self.lin_in = nn.Linear(num_features, 64)
        self.conv1 = GCNConv(64, 64)
        self.dropout = nn.Dropout(p=0.5)
        self.conv2 = GCNConv(64, 32)
        self.lin_out = nn.Linear(32, 2)
        
    def forward(self, x, edge_index, edge_attr=None):
        edge_weight = edge_attr.view(-1) if edge_attr is not None else None
        
        x = self.lin_in(x)
        x = self.conv1(x, edge_index, edge_weight=edge_weight)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.conv2(x, edge_index, edge_weight=edge_weight)
        out = self.lin_out(x)
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
