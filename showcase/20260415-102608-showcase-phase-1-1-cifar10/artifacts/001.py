import json

# Check dynamic_sgd_log.json
try:
    with open('/workspace/artifacts/r2_1/dynamic_sgd_log.json', 'r') as f:
        log = json.load(f)
        print("Log entry keys:", log[0].keys() if log else "Empty")
        print("First epoch log:", log[0])
        print("Last epoch log:", log[-1])
except Exception as e:
    print(f"Error reading log: {e}")

# Check persistence_analysis_report.json
try:
    with open('/workspace/artifacts/r2_2/persistence_analysis_report.json', 'r') as f:
        report = json.load(f)
        print("\nReport keys:", report.keys())
        # print first few items if it's a list
        if isinstance(report, list):
             print("First report item:", report[0])
        else:
             print("Report content sample:", str(report)[:500])
except Exception as e:
    print(f"Error reading report: {e}")