import json
with open('/workspace/artifacts/1/performance_report.json', 'r') as f:
    r1_report = json.load(f)
print(r1_report)