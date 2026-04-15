import os

output_files = os.listdir('/workspace/output/')
print("Files in /workspace/output/:", output_files)

# Double check best_score.json content
import json
with open('/workspace/output/best_score.json', 'r') as f:
    print("best_score.json content:", json.load(f))