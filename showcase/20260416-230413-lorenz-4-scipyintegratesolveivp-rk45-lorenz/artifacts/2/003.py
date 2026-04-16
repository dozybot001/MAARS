import os
print("Current Working Directory:", os.getcwd())
print("Files in CWD:", os.listdir('.'))
if os.path.exists('/workspace/output/'):
    print("Files in /workspace/output/:", os.listdir('/workspace/output/'))
else:
    print("/workspace/output/ does not exist")