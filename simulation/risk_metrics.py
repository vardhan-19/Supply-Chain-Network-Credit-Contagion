def calculate_ead(revenue):
    """
    Convert revenue into Exposure at Default (EAD).
    Uses standard 15% revenue turnover proxy: EAD = 0.15 * Revenue.
    """
    return revenue * 0.15

def calculate_expected_loss(pd, ead, lgd=0.45):
    """
    Calculate Expected Loss (EL): EL = PD * LGD * EAD.
    Default senior unsecured benchmark uses LGD = 0.45.
    """
    return pd * lgd * ead

def calculate_systemic_risk(baseline_pds, shocked_pds, revenues, idx_to_entity, target_idx=None):
    """
    Calculate the Systemic Risk Contribution (SRC) and identify affected counterparties.
    
    Args:
        baseline_pds: Baseline default probabilities.
        shocked_pds: Post-shock default probabilities.
        revenues: Node revenues for EAD calculation.
        idx_to_entity: Mapping from integer index to company UUID.
        target_idx: Optional integer index of the shocked company to exclude from
                    downstream contagion loss.
    """
    total_systemic_loss_increase = 0.0
    affected_nodes = []
    
    num_nodes = len(baseline_pds)
    for i in range(num_nodes):
        # Exclude the primary shocked company from downstream contagion calculation
        if target_idx is not None and i == target_idx:
            continue

        baseline_pd = float(baseline_pds[i])
        shocked_pd = float(shocked_pds[i])
        revenue = max(0.0, float(revenues[i]))  # Clamp: negative revenue → 0 EAD
        
        ead = calculate_ead(revenue)
        baseline_el = calculate_expected_loss(baseline_pd, ead)
        shocked_el = calculate_expected_loss(shocked_pd, ead)
        
        el_increase = max(0.0, shocked_el - baseline_el)
        delta_pd = shocked_pd - baseline_pd
        
        if el_increase > 0:
            total_systemic_loss_increase += el_increase
            affected_nodes.append({
                "company_id": idx_to_entity[i],
                "before_pd": baseline_pd,
                "after_pd": shocked_pd,
                "delta_pd": delta_pd,
                "el_increase": el_increase
            })
            
    return total_systemic_loss_increase, affected_nodes
