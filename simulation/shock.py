import copy
import torch
from torch_geometric.data import Data

def apply_node_shock(data: Data, target_node_idx: int) -> Data:
    """
    Simulates firm insolvency via node removal (SCR-NR).
    Removes all incident edges and zeroes out node features for the shocked firm.
    
    Args:
        data: The original PyTorch Geometric Data object.
        target_node_idx: The integer index of the node to shock.
        
    Returns:
        A new Data object with target edges removed and features zeroed.
    """
    shocked_data = copy.deepcopy(data)
    
    edge_index = shocked_data.edge_index
    mask = (edge_index[0] != target_node_idx) & (edge_index[1] != target_node_idx)
    
    shocked_data.edge_index = edge_index[:, mask]
    if shocked_data.edge_attr is not None:
        shocked_data.edge_attr = shocked_data.edge_attr[mask]
        
    if shocked_data.x is not None:
        shocked_data.x[target_node_idx] = 0.0
        
    return shocked_data

def apply_edge_shock(data: Data, source_idx: int, target_idx: int) -> Data:
    """
    Simulates a bilateral supply or credit line severance (SCR-ER).
    
    Args:
        data: The original PyTorch Geometric Data object.
        source_idx: The integer index of the source node.
        target_idx: The integer index of the target node.
        
    Returns:
        A new Data object with the specified directed edge removed.
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
