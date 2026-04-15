import torch
import json

report_path = '/workspace/artifacts/1/performance_report.json'
with open(report_path, 'r') as f:
    report = json.load(f)
print("Performance Report:", report)

model_path = '/workspace/artifacts/1/source_badnets.pth'
checkpoint = torch.load(model_path, map_location='cpu')
if isinstance(checkpoint, dict):
    print("Keys:", checkpoint.keys())
    if 'state_dict' in checkpoint:
        keys = list(checkpoint['state_dict'].keys())
    else:
        keys = list(checkpoint.keys())
else:
    keys = list(checkpoint.state_dict().keys())

print("State Dict Keys (sample):", keys[:10])