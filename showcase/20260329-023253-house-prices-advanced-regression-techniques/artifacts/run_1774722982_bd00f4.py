import os
import json

best_score_path = '/workspace/output/best_score.json'
if os.path.exists(best_score_path):
    with open(best_score_path, 'r') as f:
        print(json.load(f))
else:
    print("No best_score.json found.")