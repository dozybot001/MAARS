import json
try:
    with open('/workspace/artifacts/1/performance_report.json', 'r') as f:
        report = json.load(f)
    print(json.dumps(report, indent=2))
except Exception as e:
    print(e)