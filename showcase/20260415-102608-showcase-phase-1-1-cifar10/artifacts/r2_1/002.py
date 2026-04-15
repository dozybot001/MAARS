import os
r1_path = '/workspace/artifacts/1'
if os.path.exists(r1_path):
    print(f"Contents of {r1_path}: {os.listdir(r1_path)}")