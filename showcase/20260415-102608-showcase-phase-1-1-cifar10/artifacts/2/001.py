import os

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f'{subindent}{f}')

print("Checking /workspace/artifacts/1/")
if os.path.exists('/workspace/artifacts/1'):
    list_files('/workspace/artifacts/1')
else:
    print("/workspace/artifacts/1 does not exist.")

print("\nChecking /workspace/data/")
if os.path.exists('/workspace/data'):
    list_files('/workspace/data')
else:
    print("/workspace/data does not exist.")