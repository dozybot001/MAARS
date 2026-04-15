import json
with open('/workspace/output/best_score.json', 'r') as f:
    data = json.load(f)

data['score'] = data['score'] / 100.0 # Convert to 0-1 range
data['metric'] = 'accuracy' # Use the exact key from example

with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(data, f)