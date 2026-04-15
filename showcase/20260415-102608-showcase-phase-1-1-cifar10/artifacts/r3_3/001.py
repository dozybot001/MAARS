import os
import json

def list_files(path):
    if os.path.exists(path):
        return os.listdir(path)
    return []

print("Files in r3_1:", list_files("/workspace/artifacts/r3_1"))
print("Files in r3_2:", list_files("/workspace/artifacts/r3_2"))

# Load data if files exist
try:
    with open("/workspace/artifacts/r3_1/metrics_diff_lr.json", 'r') as f:
        metrics_diff_lr = json.load(f)
    print("\nMetrics Diff LR:", metrics_diff_lr)
except Exception as e:
    print(f"Error loading metrics_diff_lr.json: {e}")

try:
    with open("/workspace/artifacts/r3_2/metrics_high_lr.json", 'r') as f:
        metrics_high_lr = json.load(f)
    print("\nMetrics High LR:", metrics_high_lr)
except Exception as e:
    print(f"Error loading metrics_high_lr.json: {e}")