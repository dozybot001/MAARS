import json
with open('/workspace/output/best_score.json', 'r') as f:
    print(json.load(f))