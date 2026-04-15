import json
import os

# Check data directory
print("Data directory contents:")
print(os.listdir('/workspace/data/'))

# Check anchor summary
anchor_summary_path = '/workspace/artifacts/4/anchor_summary.json'
if os.path.exists(anchor_summary_path):
    with open(anchor_summary_path, 'r') as f:
        anchor_info = json.load(f)
    print("\nAnchor Summary:")
    print(json.dumps(anchor_info, indent=2))
else:
    print(f"\n{anchor_summary_path} not found.")

# Try to find what V-Ratio is. It might be mentioned in some report.
report_path = '/workspace/artifacts/4/analysis_report.md'
if os.path.exists(report_path):
    print("\nAnalysis Report Header:")
    with open(report_path, 'r') as f:
        print(f.read(500))