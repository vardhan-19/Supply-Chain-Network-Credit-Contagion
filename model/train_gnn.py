import os
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.utils.class_weight import compute_class_weight
import numpy as np

# Adjust imports to correctly refer to our files
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir) # Add root to sys.path

from model.gnn_dataset import build_dataset
from model.gnn_model import SupplyChainGNN

def train():
    # Set seed for reproducible weight initialization
    torch.manual_seed(42)
    
    # 1. Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, 'data', 'processed', 'node_features_X.csv')
    edges_csv = os.path.join(base_dir, 'data', 'processed', 'edge_features_W.csv')
    weights_dir = os.path.join(base_dir, 'model', 'weights')
    os.makedirs(weights_dir, exist_ok=True)
    best_weights_path = os.path.join(weights_dir, 'best_gnn.pt')

    # 2. Load dataset
    data = build_dataset(nodes_csv, edges_csv)
    print("Dataset loaded successfully.")
    
    # 3. Compute class weights to handle imbalance
    labels = data.y.numpy()
    classes = np.unique(labels)
    class_weights = compute_class_weight(class_weight='balanced', classes=classes, y=labels)
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"Computed class weights: {class_weights}")

    # 4. Initialize model, optimizer, loss
    num_features = data.x.shape[1]
    model = SupplyChainGNN(num_features=num_features)
    
    optimizer = optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
    criterion = nn.NLLLoss(weight=class_weights_tensor)

    # 5. Training loop
    best_test_loss = float('inf')
    best_acc = 0.0
    
    print("Starting training...")
    for epoch in range(1, 201):
        model.train()
        optimizer.zero_grad()
        
        # Forward pass
        out = model(data.x, data.edge_index, data.edge_attr)
        
        # Loss calculation (only on training nodes)
        loss = criterion(out[data.train_mask], data.y[data.train_mask])
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # Calculate test accuracy and test loss
        model.eval()
        with torch.no_grad():
            test_out = model(data.x, data.edge_index, data.edge_attr)
            test_loss = criterion(test_out[data.test_mask], data.y[data.test_mask])
            preds = test_out.argmax(dim=1)
            correct = (preds[data.test_mask] == data.y[data.test_mask]).sum().item()
            acc = correct / data.test_mask.sum().item()
        
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:03d} | Train Loss: {loss.item():.4f} | Test Loss: {test_loss.item():.4f} | Test Accuracy: {acc:.4f}")
            
        # Save best model based on test loss (prevents overfitting)
        if test_loss.item() < best_test_loss:
            best_test_loss = test_loss.item()
            best_acc = acc
            torch.save(model.state_dict(), best_weights_path)

    print(f"Training completed. Best Test Loss: {best_test_loss:.4f} | Best Test Accuracy: {best_acc:.4f}")
    print(f"Saved best model weights to: {best_weights_path}")

if __name__ == "__main__":
    train()
