import os
import torch
import pytest
from simulation.risk_metrics import calculate_ead, calculate_expected_loss, calculate_systemic_risk
from simulation.shock import apply_node_shock, apply_edge_shock
from simulation.stress_test import run_stress_test
from model.gnn_dataset import build_dataset
from model.gnn_model import SupplyChainGNN

def test_calculate_ead():
    revenue = 1000.0
    assert calculate_ead(revenue) == 150.0
    assert calculate_ead(0.0) == 0.0

def test_calculate_expected_loss():
    pd = 0.10
    ead = 200.0
    lgd = 0.45
    assert calculate_expected_loss(pd, ead, lgd) == pytest.approx(9.0)

def test_calculate_systemic_risk():
    baseline_pds = [0.10, 0.20, 0.05]
    shocked_pds = [0.10, 0.25, 0.05]
    revenues = [100.0, 200.0, 50.0]
    idx_to_entity = {0: "comp_0", 1: "comp_1", 2: "comp_2"}

    total_loss, affected = calculate_systemic_risk(
        baseline_pds, shocked_pds, revenues, idx_to_entity, target_idx=0
    )
    assert len(affected) == 1
    assert affected[0]["company_id"] == "comp_1"
    assert affected[0]["delta_pd"] == pytest.approx(0.05)
    assert total_loss > 0.0

def test_apply_node_shock():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "node_features_X.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edge_features_W.csv")
    data = build_dataset(nodes_csv, edges_csv)

    target_idx = 0
    original_edge_count = data.edge_index.shape[1]
    shocked = apply_node_shock(data, target_idx)

    assert shocked.edge_index.shape[1] < original_edge_count
    assert torch.all(shocked.x[target_idx] == 0.0)

def test_apply_edge_shock():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "node_features_X.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edge_features_W.csv")
    data = build_dataset(nodes_csv, edges_csv)

    src = int(data.edge_index[0, 0])
    tgt = int(data.edge_index[1, 0])
    original_count = data.edge_index.shape[1]

    shocked = apply_edge_shock(data, src, tgt)
    assert shocked.edge_index.shape[1] < original_count

def test_run_stress_test_node_and_edge():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "node_features_X.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edge_features_W.csv")
    weights_path = os.path.join(base_dir, "model", "weights", "best_gnn.pt")

    data = build_dataset(nodes_csv, edges_csv)
    model = SupplyChainGNN(num_features=data.x.shape[1])
    model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
    model.eval()

    sample_uuid = list(data.entity_to_idx.keys())[0]
    result_node = run_stress_test(model, data, sample_uuid, shock_type="node_removal")
    assert result_node["shock_type"] == "node_removal"
    assert "total_systemic_loss_increase" in result_node

    src_uuid = list(data.entity_to_idx.keys())[0]
    tgt_uuid = list(data.entity_to_idx.keys())[1]
    result_edge = run_stress_test(model, data, tgt_uuid, shock_type="edge_removal", source_uuid=src_uuid)
    assert result_edge["shock_type"] == "edge_removal"
    assert "total_systemic_loss_increase" in result_edge
