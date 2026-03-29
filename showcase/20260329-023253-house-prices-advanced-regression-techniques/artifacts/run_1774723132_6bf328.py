import json
with open('/workspace/output/lightgbm_results.json', 'r') as f:
    print(json.dumps(json.load(f), indent=2))