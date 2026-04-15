import json
import torch

# Load metrics from r3_1
try:
    with open('/workspace/artifacts/r3_1/metrics_diff_lr.json', 'r') as f:
        metrics_r3_1 = json.load(f)
    print("Metrics from r3_1:")
    print(json.dumps(metrics_r3_1, indent=2))
except Exception as e:
    print(f"Error loading metrics: {e}")

# Try to check the model structure from source_badnets.pth
try:
    state_dict = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')
    print("\nKeys in state_dict (first 10):")
    print(list(state_dict.keys())[:10])
    
    # Check output layer to confirm class count
    last_layer_key = list(state_dict.keys())[-1]
    print(f"\nLast layer key: {last_layer_key}, shape: {state_dict[last_layer_key].shape}")
except Exception as e:
    print(f"Error loading model: {e}")