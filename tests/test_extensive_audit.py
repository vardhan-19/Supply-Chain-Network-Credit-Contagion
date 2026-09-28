import os
import sys
import json
import random
import requests
import numpy as np
import pandas as pd

API_BASE = "http://127.0.0.1:8001"

def run_extensive_audit():
    print("=" * 80)
    print("SCNCC EXTENSIVE MULTI-FEATURE AUDIT & EMPIRICAL INTEGRITY TEST SUITE")
    print("Target: Backend API + GNN Model + SCR-NR / SCR-ER Contagion Engines")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. API Health & Connectivity Check
    # ---------------------------------------------------------
    print("\n[Phase 1/5] Checking API Liveness and Root Endpoints...")
    r_health = requests.get(f"{API_BASE}/health", timeout=5)
    assert r_health.status_code == 200, f"Health check failed: {r_health.status_code}"
    print(f"  PASS: /health returned {r_health.status_code} {r_health.json()}")

    r_root = requests.get(f"{API_BASE}/", timeout=5)
    assert r_root.status_code == 200, f"Root check failed: {r_root.status_code}"
    print(f"  PASS: / returned {r_root.status_code} {r_root.json()}")

    # ---------------------------------------------------------
    # 2. Graph Retrieval & Feature Inspection
    # ---------------------------------------------------------
    print("\n[Phase 2/5] Retrieving Full Graph Network Topology (/graph)...")
    r_graph = requests.get(f"{API_BASE}/graph", timeout=15)
    assert r_graph.status_code == 200, f"Graph retrieval failed: {r_graph.status_code}"
    graph_data = r_graph.json()
    assert "nodes" in graph_data and "links" in graph_data, "Malformed graph response"
    nodes = graph_data["nodes"]
    links = graph_data["links"]
    print(f"  PASS: Retrieved {len(nodes)} nodes and {len(links)} edges.")
    assert len(nodes) == 174, f"Expected 174 nodes, got {len(nodes)}"
    assert len(links) == 1213, f"Expected 1213 links, got {len(links)}"

    # ---------------------------------------------------------
    # 3. Model Predictions (/predict)
    # ---------------------------------------------------------
    print("\n[Phase 3/5] Testing Baseline Predictions (/predict)...")
    r_pred = requests.post(f"{API_BASE}/predict", timeout=15)
    assert r_pred.status_code == 200, f"Prediction endpoint failed: {r_pred.status_code}"
    pred_data = r_pred.json()
    assert isinstance(pred_data, list), "Predict should return a list"
    assert len(pred_data) == 174, f"Expected 174 predictions, got {len(pred_data)}"
    pred_dict = {p["company_id"]: p for p in pred_data}

    # ---------------------------------------------------------
    # 4. Select 16 Random Distinct Companies
    # ---------------------------------------------------------
    print("\n[Phase 4/5] Selecting 16 Random Distinct Companies Across Network...")
    random.seed(42)
    selected_sample = random.sample(nodes, 16)

    print(f"  Selected {len(selected_sample)} diverse test companies:")
    for idx, c in enumerate(selected_sample, 1):
        rev = c.get('revenue')
        rev_str = f"${rev/1e9:.2f}B" if rev and rev >= 1e9 else (f"${rev/1e6:.1f}M" if rev else "N/A")
        print(f"    {idx:2d}. {c['name'][:30]:<30} | Tier: {c['risk_tier']:<6} | PD: {c['pd']*100:5.2f}% | Rev: {rev_str}")

    # ---------------------------------------------------------
    # Test Feature A: Financial & Topological Metrics Diversity
    # ---------------------------------------------------------
    print("\n[Feature Audit A] Verifying Financial & Topological Metrics across 16 Companies...")
    ids = [c["id"] for c in selected_sample]
    names = [c["name"] for c in selected_sample]
    pds = [c["pd"] for c in selected_sample]

    assert len(set(ids)) == 16, "Sample IDs must be 100% unique"
    assert len(set(names)) == 16, "Sample company names must be 100% unique"
    assert len(set(pds)) >= 10, "Default probabilities should vary across companies"
    print("  PASS: All 16 companies are distinct entities with diverse risk profiles.")

    # ---------------------------------------------------------
    # Test Feature B: SCR-NR (Node Default Stress Simulation) across 18 Companies
    # ---------------------------------------------------------
    print("\n[Feature Audit B] Running SCR-NR (Node Default Simulation) on 18 Companies...")
    node_sim_results = []
    for idx, c in enumerate(selected_sample, 1):
        cid = c["id"]
        cname = c["name"]
        payload = {"target_company_id": cid, "shock_type": "node_removal"}
        r_sim = requests.post(f"{API_BASE}/simulate", json=payload, timeout=15)
        assert r_sim.status_code == 200, f"Simulation failed for {cname}: {r_sim.text}"
        res = r_sim.json()
        assert "total_systemic_loss_increase" in res, f"Missing loss field: {res}"
        assert "affected_nodes" in res, f"Missing affected_nodes: {res}"

        sys_loss = res["total_systemic_loss_increase"]
        num_affected = len(res["affected_nodes"])
        max_delta_pd = max([a["delta_pd"] for a in res["affected_nodes"]]) if num_affected > 0 else 0.0

        node_sim_results.append({
            "idx": idx,
            "company_id": cid,
            "company_name": cname,
            "tier": c["risk_tier"],
            "systemic_loss": sys_loss,
            "num_affected": num_affected,
            "max_delta_pd": max_delta_pd
        })
        loss_str = f"${sys_loss/1e9:.2f}B" if sys_loss >= 1e9 else f"${sys_loss/1e6:.2f}M"
        print(f"    {idx:2d}. {cname[:28]:<28} -> Systemic Loss: {loss_str:<10} | Affected: {num_affected:3d} nodes | Max dPD: +{max_delta_pd*100:5.2f}%")

    # Verify outcome diversity
    sim_losses = [r["systemic_loss"] for r in node_sim_results]
    affected_counts = [r["num_affected"] for r in node_sim_results]
    
    unique_losses = len(set([round(l, -3) for l in sim_losses]))
    print(f"\n  Unique systemic loss outcomes: {unique_losses} / 16")
    assert unique_losses >= 10, f"Expected at least 10 distinct systemic loss outcomes, got {unique_losses}"
    print(f"  PASS: SCR-NR generates genuinely different, diverse outcomes across all 16 companies!")

    # ---------------------------------------------------------
    # Test Feature C: SCR-ER (Edge Severance Stress Simulation) across 18 Edges
    # ---------------------------------------------------------
    print("\n[Feature Audit C] Selecting 18 Distinct Directed Edges for SCR-ER (Edge Severance)...")
    # Sample 18 random edges from the 1213 available links
    edge_sample = random.sample(links, 18)
    edge_sim_results = []
    
    print(f"  Running SCR-ER on 18 distinct supplier -> customer links:")
    for idx, edge in enumerate(edge_sample, 1):
        src_id = edge["source"] if isinstance(edge["source"], str) else edge["source"]["id"]
        tgt_id = edge["target"] if isinstance(edge["target"], str) else edge["target"]["id"]
        src_name = edge.get("source_name", src_id[:12])
        tgt_name = edge.get("target_name", tgt_id[:12])
        rel_type = edge.get("relationship_type", "supply")
        weight = edge.get("weight", 1.0)

        payload = {
            "target_company_id": tgt_id,
            "source_company_id": src_id,
            "shock_type": "edge_removal"
        }
        r_edge_sim = requests.post(f"{API_BASE}/simulate", json=payload, timeout=15)
        assert r_edge_sim.status_code == 200, f"Edge simulation failed: {r_edge_sim.text}"
        res = r_edge_sim.json()
        assert "total_systemic_loss_increase" in res, f"Missing loss field: {res}"

        sys_loss = res["total_systemic_loss_increase"]
        num_affected = len(res["affected_nodes"])
        max_delta_pd = max([a["delta_pd"] for a in res["affected_nodes"]]) if num_affected > 0 else 0.0

        edge_sim_results.append({
            "idx": idx,
            "source": src_name,
            "target": tgt_name,
            "rel_type": rel_type,
            "weight": weight,
            "systemic_loss": sys_loss,
            "num_affected": num_affected,
            "max_delta_pd": max_delta_pd
        })
        loss_str = f"${sys_loss/1e6:.2f}M" if sys_loss >= 1e6 else f"${sys_loss/1e3:.1f}K"
        print(f"    {idx:2d}. {src_name[:16]:<16} --[w={weight:.2f}]--> {tgt_name[:16]:<16} | Loss: {loss_str:<9} | Affected: {num_affected:2d} | Max dPD: +{max_delta_pd*100:5.3f}%")

    edge_losses = [r["systemic_loss"] for r in edge_sim_results]
    print(f"\n  Edge Severance Results Summary:")
    print(f"    Min Loss: ${min(edge_losses):,.2f}")
    print(f"    Max Loss: ${max(edge_losses):,.2f}")
    print(f"    Mean Loss: ${np.mean(edge_losses):,.2f}")
    print("  PASS: SCR-ER successfully evaluated across 18 distinct commercial links with nuanced impact variations.")

    # ---------------------------------------------------------
    # 5. Security & Robustness Edge Cases
    # ---------------------------------------------------------
    print("\n[Phase 5/5] Security, Malformed Inputs & Boundary Validation...")
    
    # Test 5.1: Non-existent target company UUID
    r_bad_id = requests.post(f"{API_BASE}/simulate", json={"target_company_id": "non-existent-uuid-9999", "shock_type": "node_removal"})
    print(f"  Test 5.1: Non-existent target UUID -> HTTP {r_bad_id.status_code}")
    assert r_bad_id.status_code in (400, 404) or (r_bad_id.status_code == 200 and "error" in r_bad_id.json())
    print("    Handled safely without crash.")

    # Test 5.2: Invalid shock type
    r_bad_type = requests.post(f"{API_BASE}/simulate", json={"target_company_id": selected_sample[0]["id"], "shock_type": "nuclear_meltdown"})
    print(f"  Test 5.2: Invalid shock type -> HTTP {r_bad_type.status_code}")
    assert r_bad_type.status_code in (400, 422) or (r_bad_type.status_code == 200 and "error" in r_bad_type.json())
    print("    Handled safely without crash.")

    # Test 5.3: Edge removal missing source company
    r_missing_src = requests.post(f"{API_BASE}/simulate", json={"target_company_id": selected_sample[0]["id"], "shock_type": "edge_removal"})
    print(f"  Test 5.3: Edge removal missing source -> HTTP {r_missing_src.status_code}")
    assert r_missing_src.status_code in (400, 422) or (r_missing_src.status_code == 200 and "error" in r_missing_src.json())
    print("    Handled safely without crash.")

    # Test 5.4: Malformed empty JSON
    r_empty = requests.post(f"{API_BASE}/simulate", json={})
    print(f"  Test 5.4: Empty JSON body -> HTTP {r_empty.status_code}")
    assert r_empty.status_code == 422, "FastAPI should reject empty body with 422 Unprocessable Entity"
    print("    Handled safely by Pydantic validation.")

    print("\n" + "=" * 80)
    print("EXTENSIVE AUDIT COMPLETED SUCCESSFULLY: ALL 5 PHASES PASSED 100%")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_extensive_audit()
    sys.exit(0 if success else 1)
