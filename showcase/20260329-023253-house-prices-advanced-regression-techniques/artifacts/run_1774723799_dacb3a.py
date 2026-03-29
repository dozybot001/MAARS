import json

files = ['best_score.json', 'ensemble_results.json', 'final_ensemble_results.json']
results = {}

for f in files:
    try:
        with open(f'/workspace/outputs/{f}', 'r') as file:
            results[f] = json.load(file)
    except FileNotFoundError:
        try:
            with open(f, 'r') as file:
                results[f] = json.load(file)
        except:
            results[f] = "File not found"

print(json.dumps(results, indent=2))