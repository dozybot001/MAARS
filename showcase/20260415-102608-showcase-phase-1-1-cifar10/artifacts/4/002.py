import json

try:
    with open('/workspace/artifacts/1/performance_report.json', 'r') as f:
        report = json.load(f)
        print("Task 1 Performance Report:")
        print(json.dumps(report, indent=4))
except Exception as e:
    print(f"Error reading Task 1 report: {e}")