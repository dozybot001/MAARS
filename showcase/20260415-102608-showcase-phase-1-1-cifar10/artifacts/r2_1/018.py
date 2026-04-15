import os
import json

print("Files in /workspace/output:")
print(os.listdir('/workspace/output'))

with open('/workspace/output/dynamic_sgd_log.json', 'r') as f:
    log = json.load(f)
    print("\nLog content (first entry):")
    print(log[0])
    print("\nLog content (last entry):")
    print(log[-1])

print("\nBest score:")
with open('/workspace/output/best_score.json', 'r') as f:
    print(json.load(f))