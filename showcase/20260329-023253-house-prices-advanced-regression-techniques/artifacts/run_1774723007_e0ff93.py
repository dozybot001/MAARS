import json
with open('/workspace/output/linear_models_results.json', 'r') as f:
    print(json.dumps(json.load(f), indent=4))