import json
try:
    with open('/workspace/artifacts/4/anchor_summary.json', 'r') as f:
        adam_summary = json.load(f)
    print("Adam Summary Keys:", adam_summary.keys())
    print("Adam Summary Content Sample:", str(adam_summary)[:500])
except Exception as e:
    print(f"Error loading Adam summary: {e}")