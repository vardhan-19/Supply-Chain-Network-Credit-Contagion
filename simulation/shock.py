import copy
import torch
from torch_geometric.data import Data

def apply_node_shock(data: Data, target_node_idx: int) -> Data:
    """
    Simulates a company bankruptcy (Shock Injection - Node Removal (SCR-NR)).
    
    Args:
        data: The original PyTorch Geometric Data object.
        target_node_idx: The integer index of the node to shock (simulate bankruptcy).
        
    Returns:
        A new Data object with the target node's edges removed and features zeroed out.
    """
    # Deep copy to avoid mutating the original data (clone() is shallow and shares memory)
    shocked_data = copy.deepcopy(data)
    
    # Find all edges where the source or target is target_node_idx and remove them
    edge_index = shocked_data.edge_index
    mask = (edge_index[0] != target_node_idx) & (edge_index[1] != target_node_idx)
    
    # Update edge_index to match the new masked edges
    shocked_data.edge_index = edge_index[:, mask]
    
    # Update edge_attr to match the new edge_index
    if shocked_data.edge_attr is not None:
        shocked_data.edge_attr = shocked_data.edge_attr[mask]
        
    # Set the target node's features in data.x to reflect bankruptcy 
    # Zeroing out all features to represent e.g., revenue to 0, extreme state
    if shocked_data.x is not None:
        shocked_data.x[target_node_idx] = 0.0
        
    return shocked_data

def apply_edge_shock(data: Data, source_idx: int, target_idx: int) -> Data:
    """
    Simulates a severed supply or credit line (Shock Injection - Edge Removal (SCR-ER)).
    
    Args:
        data: The original PyTorch Geometric Data object.
        source_idx: The integer index of the source node.
        target_idx: The integer index of the target node.
        
    Returns:
        A new Data object with exactly one edge removed (if it existed).
    """
    # Deep copy to avoid mutating the original data (clone() is shallow and shares memory)
    shocked_data = copy.deepcopy(data)
    
    # Find the specific edge in edge_index between source_idx and target_idx
    edge_index = shocked_data.edge_index
    mask = ~((edge_index[0] == source_idx) & (edge_index[1] == target_idx))
    
    # Remove the edge and update edge_attr accordingly
    shocked_data.edge_index = edge_index[:, mask]
    if shocked_data.edge_attr is not None:
        shocked_data.edge_attr = shocked_data.edge_attr[mask]
        
    return shocked_data
