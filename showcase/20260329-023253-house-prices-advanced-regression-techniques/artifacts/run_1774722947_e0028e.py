import os
import subprocess

def find_dir(name):
    for root, dirs, files in os.walk('/workspace'):
        if name in dirs:
            return os.path.join(root, name)
    return None

print(f"Searching for 'artifacts' in /workspace: {find_dir('artifacts')}")
print(f"Searching for 'output' in /workspace: {find_dir('output')}")

# Where are my files?
print(f"Files in /workspace/output: {os.listdir('/workspace/output')}")