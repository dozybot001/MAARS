import json

report_path = '/workspace/artifacts/1/performance_report.json'
with open(report_path, 'r') as f:
    report = json.load(f)
    print(json.dumps(report, indent=4))