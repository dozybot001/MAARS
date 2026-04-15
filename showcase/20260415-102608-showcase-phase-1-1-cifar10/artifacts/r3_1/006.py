import json
import os

# Confirm artifacts
artifacts = ['diff_lr_ft_model.pth', 'metrics_diff_lr.json', 'best_score.json']
for art in artifacts:
    if os.path.exists(art):
        print(f"Found artifact: {art} ({os.path.getsize(art)} bytes)")
    else:
        # Check /workspace/output/ for best_score.json
        alt_path = os.path.join('/workspace/output/', art)
        if os.path.exists(alt_path):
            print(f"Found artifact at {alt_path}: {art} ({os.path.getsize(alt_path)} bytes)")
        else:
            print(f"Missing artifact: {art}")

# Check json content
with open('metrics_diff_lr.json', 'r') as f:
    data = json.load(f)
    print(f"Metrics count: {len(data)}")
    print("Last epoch entry:", data[-1])