import pandas as pd
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

def main():
    # File paths (dynamically resolved relative to project root)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_csv = os.path.join(base_dir, "data", "processed", "node_features_X.csv")
    output_model_dir = os.path.join(base_dir, "model", "evaluation")
    output_metrics_file = os.path.join(output_model_dir, "baseline_metrics.json")
    
    # Ensure output directory exists
    os.makedirs(output_model_dir, exist_ok=True)
    
    # Load dataset
    df = pd.read_csv(input_csv)
    
    # Check if 'degree' exists, else create from in_degree and out_degree
    if 'degree' not in df.columns:
        if 'in_degree' in df.columns and 'out_degree' in df.columns:
            df['degree'] = df['in_degree'] + df['out_degree']
        else:
            raise ValueError("'degree' column missing and cannot be computed from 'in_degree' and 'out_degree'")
            
    # Select feature columns
    feature_cols = ['revenue', 'total_debt', 'debt_to_equity', 'current_ratio', 'profit_margin', 'degree', 'betweenness_centrality', 'pagerank']
    X = df[feature_cols].copy()
    
    # Fill missing values with 0
    X = X.fillna(0)
    
    # Extract target y
    y = df['default_label']
    
    # Train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train LogisticRegression
    model = LogisticRegression(class_weight='balanced', random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # Predict and evaluate
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    
    metrics = {
        "Precision": precision_score(y_test, y_pred, zero_division=0),
        "Recall": recall_score(y_test, y_pred, zero_division=0),
        "F1-Score": f1_score(y_test, y_pred, zero_division=0),
        "AUC-ROC": roc_auc_score(y_test, y_prob)
    }
    
    # Save metrics to json
    with open(output_metrics_file, 'w') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Baseline model evaluated successfully.")
    print(f"Metrics saved to {output_metrics_file}")
    print(json.dumps(metrics, indent=4))

if __name__ == "__main__":
    main()
