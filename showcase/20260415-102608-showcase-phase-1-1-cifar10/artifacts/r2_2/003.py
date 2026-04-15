import glob

files = glob.glob('/workspace/artifacts/**/*log*.json', recursive=True)
print("Found log files:", files)

# Also check for .csv or other json files in /workspace/artifacts/4/
files_t4 = glob.glob('/workspace/artifacts/4/*')
print("Task 4 files:", files_t4)