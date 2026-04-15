import json
with open('v_stats_report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=4))