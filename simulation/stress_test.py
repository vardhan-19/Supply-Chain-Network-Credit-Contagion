import torch
from simulation.shock import apply_node_shock, apply_edge_shock
from simulation.risk_metrics import calculate_systemic_risk

def run_stress_test(model, data, target_uuid, shock_type="node_removal", source_uuid=None):
    """
    Orchestrate the shock, the GNN prediction, and the risk calculation.
    
    Args:
        model: Trained GNN model.
        data: PyG Data object with entity_to_idx/idx_to_entity mappings.
        target_uuid: UUID of the company to shock (node removal) or the target
                     node of the edge to sever (edge removal).
        shock_type: "node_removal" or "edge_removal".
        source_uuid: UUID of the source node for edge removal (required when
                     shock_type="edge_removal"). The edge source_uuid → target_uuid
                     will be removed.
    """
    if not hasattr(data, 'entity_to_idx'):
        raise ValueError("Data object must have 'entity_to_idx' mapping attached.")
        
    if target_uuid not in data.entity_to_idx:
        raise ValueError(f"Company ID '{target_uuid}' not found in the dataset.")
        
    node_idx = data.entity_to_idx[target_uuid]
    
    model.eval()
    with torch.no_grad():
        baseline_output = model(data.x, data.edge_index, data.edge_attr)
        # Assuming output is log_softmax, extract exp() for probabilities of class 1
        baseline_pds = torch.exp(baseline_output)[:, 1]
        
    if shock_type == "node_removal":
        shocked_data = apply_node_shock(data, node_idx)
    elif shock_type == "edge_removal":
        if source_uuid is None:
            raise ValueError("source_uuid is required for edge_removal shock type.")
        if source_uuid not in data.entity_to_idx:
            raise ValueError(f"Source company ID '{source_uuid}' not found in the dataset.")
        source_idx = data.entity_to_idx[source_uuid]
        shocked_data = apply_edge_shock(data, source_idx, node_idx)
    else:
        raise NotImplementedError(f"Shock type '{shock_type}' not implemented.")
        
    with torch.no_grad():
        shocked_output = model(shocked_data.x, shocked_data.edge_index, shocked_data.edge_attr)
        shocked_pds = torch.exp(shocked_output)[:, 1]
        
    # Extract raw revenues for financial metric calculation. 
    # Fallback to data.x[:, 0] if raw_revenue is not attached.
    revenues = data.raw_revenue if hasattr(data, 'raw_revenue') else data.x[:, 0]
    
    # For node removal, exclude the shocked target from downstream contagion calculation
    # For edge removal, neither node is bankrupt (only the link is cut), so downstream impacts on both can be measured
    excluded_idx = node_idx if shock_type == "node_removal" else None
    
    total_systemic_loss_increase, affected_nodes = calculate_systemic_risk(
        baseline_pds, shocked_pds, revenues, data.idx_to_entity, target_idx=excluded_idx
    )
    
    result = {
        "shocked_company": target_uuid,
        "shock_type": shock_type,
        "total_systemic_loss_increase": total_systemic_loss_increase,
        "affected_nodes": affected_nodes
    }
    if shock_type == "edge_removal":
        result["source_company"] = source_uuid
    return result

