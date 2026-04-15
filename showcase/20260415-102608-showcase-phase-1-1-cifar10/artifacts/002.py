import os
import json

path1 = '/workspace/artifacts/r2_1/dynamic_sgd_log.json'
if os.path.exists(path1):
    with open(path1, 'r') as f:
        data = json.load(f)
        print("r2_1 Log (last epoch):", data[-1])
else:
    print("r2_1 log not found")

path2 = '/workspace/artifacts/r2_2/persistence_analysis_report.json'
if os.path.exists(path2):
    with open(path2, 'r') as f:
        data = json.load(f)
        print("r2_2 Report summary:", str(data)[:200])
else:
    print("r2_2 report not found")