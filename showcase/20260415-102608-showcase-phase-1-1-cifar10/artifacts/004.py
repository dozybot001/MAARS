import os
import json

def read_json(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return f"File {path} not found"

# Try different possible paths
paths = [
    '/workspace/artifacts/r3_3/v_stats_report.json',
    'artifacts/r3_3/v_stats_report.json',
    '../artifacts/r3_3/v_stats_report.json',
    'r3_3/v_stats_report.json'
]

results = {}
for p in paths:
    results[p] = read_json(p)

print(json.dumps(results, indent=2))