import json
import os

best_score = {
    "metric": "ASR-T_at_45pct_Acc",
    "score": 0.3949,
    "model": "Differential_LR_FT",
    "details": "At Clean Acc 44.81%, ASR-T is 39.49%, V-Ratio is 3.11, while High LR FT erases it to 0.23%."
}

with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(best_score, f)

print("Saved best_score.json")