import os
import json

# Move files to /workspace/output if they are in the current dir
if os.path.exists('full_ft_model.pth'):
    os.rename('full_ft_model.pth', '/workspace/output/full_ft_model.pth')

print("Output directory files:", os.listdir('/workspace/output/'))
if os.path.exists('/workspace/output/best_score.json'):
    with open('/workspace/output/best_score.json', 'r') as f:
        print("Score data:", json.load(f))