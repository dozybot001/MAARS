import os
import json

# List artifacts
artifacts = os.listdir('.')
print(f"Artifacts: {artifacts}")

# Check content of metrics_high_lr.json
with open('metrics_high_lr.json', 'r') as f:
    metrics = json.load(f)
    print(f"Number of epochs recorded: {len(metrics)}")
    print(f"Last epoch metrics: {metrics[-1]}")

# Check model file size
print(f"Model file size: {os.path.getsize('high_lr_ft_model.pth') / 1024 / 1024:.2f} MB")