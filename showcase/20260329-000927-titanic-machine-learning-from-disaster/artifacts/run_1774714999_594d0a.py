import json

with open('best_model_params.json', 'r') as f:
    params = json.load(f)
    print(json.dumps(params, indent=4))