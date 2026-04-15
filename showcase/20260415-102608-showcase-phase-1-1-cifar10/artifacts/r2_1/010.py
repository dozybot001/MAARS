import json
with open('/workspace/artifacts/1/best_score.json', 'r') as f:
    print(json.load(f))