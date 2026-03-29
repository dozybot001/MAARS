import json

with open('/workspace/output/final_ensemble_results.json', 'r') as f:
    print(json.load(f))