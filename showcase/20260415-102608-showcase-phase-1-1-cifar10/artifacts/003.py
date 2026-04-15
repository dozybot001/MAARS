import json

with open('artifacts/r3_3/v_stats_report.json', 'r') as f:
    v_stats = json.load(f)

with open('artifacts/r3_1/metrics_diff_lr.json', 'r') as f:
    diff_lr_metrics = json.load(f)

print("V-Stats Report:")
print(json.dumps(v_stats, indent=2))
print("\nDiff LR Final Epoch Metrics:")
print(json.dumps(diff_lr_metrics[-1], indent=2))