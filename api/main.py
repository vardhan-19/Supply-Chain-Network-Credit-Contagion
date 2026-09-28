from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import pandas as pd
import os
import sys
import torch

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir) # Make root importable for scripts run directly

from model.gnn_dataset import build_dataset
from model.gnn_model import SupplyChainGNN
from simulation.stress_test import run_stress_test

class SimulateRequest(BaseModel):
    target_company_id: str
    shock_type: str = "node_removal"
    source_company_id: str = None

# --- Global Cache for API Performance Optimization ---
GLOBAL_STATE = {
    "model": None,
    "data": None,
    "nodes_df": None,
    "edges_df": None
}

def load_globals():
    if GLOBAL_STATE["model"] is not None:
        return

    nodes_path = os.path.join(base_dir, 'data', 'processed', 'node_features_X.csv')
    if not os.path.exists(nodes_path):
        nodes_path = os.path.join(base_dir, 'static_offline_folder', 'data', 'processed', 'node_features_X.csv')

    edges_path = os.path.join(base_dir, 'data', 'processed', 'edge_features_W.csv')
    if not os.path.exists(edges_path):
        edges_path = os.path.join(base_dir, 'static_offline_folder', 'data', 'processed', 'edge_features_W.csv')

    weights_path = os.path.join(base_dir, 'model', 'weights', 'best_gnn.pt')
    if not os.path.exists(weights_path):
        weights_path = os.path.join(base_dir, 'static_offline_folder', 'model', 'weights', 'best_gnn.pt')
    
    if not os.path.exists(weights_path) or not os.path.exists(nodes_path) or not os.path.exists(edges_path):
        raise FileNotFoundError("Missing data or model weights. Please run training first.")
        
    GLOBAL_STATE["nodes_df"] = pd.read_csv(nodes_path)
    GLOBAL_STATE["edges_df"] = pd.read_csv(edges_path)
    
    data = build_dataset(nodes_path, edges_path)
    GLOBAL_STATE["data"] = data
    
    num_features = data.x.shape[1]
    model = SupplyChainGNN(num_features=num_features)
    model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu'), weights_only=True))
    model.eval()
    GLOBAL_STATE["model"] = model

# --- Initializing the FastAPI Application Skeleton ---
app = FastAPI(title="Supply Chain Network Credit Contagion API")

# Security: explicit allowed origins only — wildcard + credentials is rejected by browsers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@app.on_event("startup")
def startup_event():
    try:
        load_globals()
        print("Successfully loaded model and dataset into memory.")
    except Exception as e:
        print(f"Warning: Could not load model/data at startup: {e}")

@app.get("/health")
def health_check():
    """Lightweight liveness probe — responds immediately even before model loads."""
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {
        "status": "running",
        "message": "Supply Chain Contagion API",
        "version": "0.1.0"
    }

@app.get("/graph")
def get_graph():
    try:
        load_globals()
    except Exception as e:
        return {"error": str(e)}
        
    nodes_df = GLOBAL_STATE["nodes_df"]
    edges_df = GLOBAL_STATE["edges_df"]
    
    predictions = predict_default()
    pred_dict = {p['company_id']: p for p in predictions} if not isinstance(predictions, dict) or "error" not in predictions else {}
    
    nodes = []
    for _, row in nodes_df.iterrows():
        entity_id = str(row['entity_id'])
        pred = pred_dict.get(entity_id, {})

        # Helper: safely get numeric value, converting NaN/inf to None for valid JSON serialization
        def safe_float(col):
            val = row.get(col, None)
            if val is None or pd.isna(val):
                return None
            try:
                f = float(val)
                if np.isnan(f) or np.isinf(f):
                    return None
                return f
            except (ValueError, TypeError):
                return None

        # Clean string / identifier fields
        c_name = row.get('company_name')
        name_str = str(c_name).strip() if pd.notna(c_name) and str(c_name).strip() and str(c_name).lower() != 'nan' else 'Unknown'

        t_val = row.get('ticker')
        ticker_str = str(t_val).strip() if pd.notna(t_val) and str(t_val).strip() and str(t_val).lower() != 'nan' else None

        conf_val = row.get('data_confidence')
        conf_str = str(conf_val).strip() if pd.notna(conf_val) and str(conf_val).strip() and str(conf_val).lower() != 'nan' else None

        is_sub_val = row.get('is_subsidiary', False)
        is_sub = bool(is_sub_val) if pd.notna(is_sub_val) else False

        dl_val = row.get('default_label', 0)
        d_label = int(dl_val) if pd.notna(dl_val) else 0

        pd_val = pred.get("pd", 0.0)
        try:
            pd_clean = float(pd_val) if not (pd.isna(pd_val) or np.isnan(pd_val) or np.isinf(pd_val)) else 0.0
        except (ValueError, TypeError):
            pd_clean = 0.0

        r_tier = pred.get("risk_tier", "Low")
        tier_clean = str(r_tier) if pd.notna(r_tier) and str(r_tier).strip() else "Low"

        nodes.append({
            # Identity
            "id":               entity_id,
            "name":             name_str,
            "ticker":           ticker_str,
            "is_subsidiary":    is_sub,
            "data_confidence":  conf_str,

            # Core financials
            "revenue":          safe_float('revenue'),
            "total_debt":       safe_float('total_debt'),
            "market_cap":       safe_float('market_cap'),
            "current_ratio":    safe_float('current_ratio'),
            "debt_to_equity":   safe_float('debt_to_equity'),
            "profit_margin":    safe_float('profit_margin'),
            "revenue_growth":   safe_float('revenue_growth'),
            "interest_coverage":safe_float('interest_coverage'),
            "roa":              safe_float('roa'),

            # Network topology
            "betweenness":           safe_float('betweenness_centrality'),
            "pagerank":              safe_float('pagerank'),
            "in_degree":             safe_float('in_degree'),
            "out_degree":            safe_float('out_degree'),
            "eigenvector_centrality":safe_float('eigenvector_centrality'),
            "clustering_coefficient":safe_float('clustering_coefficient'),

            # Credit / ML labels
            "default_label":    d_label,
            "pd":               pd_clean,
            "risk_tier":        tier_clean,
        })
        
    id_to_name = {
        str(k): (str(v).strip() if pd.notna(v) and str(v).strip() and str(v).lower() != 'nan' else 'Unknown')
        for k, v in zip(nodes_df['entity_id'], nodes_df['company_name'])
    }

    edges = []
    for _, row in edges_df.iterrows():
        source_id = str(row['source_id'])
        target_id = str(row['target_id'])

        w_raw = row.get('w_ij', 1.0)
        try:
            w_float = float(w_raw)
            if np.isnan(w_float) or np.isinf(w_float):
                w_float = 1.0
        except (ValueError, TypeError):
            w_float = 1.0

        rel_raw = row.get('relationship_type', 'unknown')
        rel_str = str(rel_raw).strip() if pd.notna(rel_raw) and str(rel_raw).strip() and str(rel_raw).lower() != 'nan' else 'unknown'

        edges.append({
            "source": source_id,
            "target": target_id,
            "weight": w_float,
            "relationship_type": rel_str,
            "source_name": id_to_name.get(source_id, 'Unknown'),
            "target_name": id_to_name.get(target_id, 'Unknown'),
        })
        
    return {
        "nodes": nodes,
        "links": edges
    }

@app.post("/predict")
def predict_default():
    try:
        load_globals()
    except Exception as e:
        return {"error": str(e)}
        
    data = GLOBAL_STATE["data"]
    model = GLOBAL_STATE["model"]
    nodes_df = GLOBAL_STATE["nodes_df"]
    
    with torch.no_grad():
        output = model(data.x, data.edge_index, data.edge_attr)
        pd_values = torch.exp(output)[:, 1].numpy()
        
    results = []
    for _, row in nodes_df.iterrows():
        entity_id = row['entity_id']
        tensor_idx = data.entity_to_idx.get(entity_id)
        if tensor_idx is None:
            continue
            
        pd_val = float(pd_values[tensor_idx])
        
        if pd_val >= 0.5:
            risk_tier = "High"
        elif pd_val >= 0.2:
            risk_tier = "Medium"
        else:
            risk_tier = "Low"
            
        results.append({
            "company_id": entity_id,
            "company_name": row['company_name'],
            "pd": pd_val,
            "risk_tier": risk_tier
        })
        
    return results

@app.post("/simulate")
def simulate_shock(request: SimulateRequest):
    try:
        load_globals()
    except Exception as e:
        return {"error": str(e)}
        
    data = GLOBAL_STATE["data"]
    model = GLOBAL_STATE["model"]
    
    # Validate edge_removal requires source_company_id
    if request.shock_type == "edge_removal" and not request.source_company_id:
        return {"error": "source_company_id is required for edge_removal shock type."}
    
    try:
        result = run_stress_test(
            model, data,
            request.target_company_id,
            shock_type=request.shock_type,
            source_uuid=request.source_company_id
        )
        return result
    except Exception as e:
        return {"error": f"Simulation failed: {str(e)}"}
