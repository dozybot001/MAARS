import json

files = [
    'linear_models_results.json',
    'xgboost_results.json',
    'lightgbm_results.json',
    'final_ensemble_details.json'
]

results = {}
for f in files:
    try:
        with open(f'/workspace/output/{f}', 'r') as jf:
            results[f] = json.load(jf)
    except Exception as e:
        results[f] = str(e)

print(json.dumps(results, indent=2))