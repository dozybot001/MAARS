import os
print("Root:", os.listdir('/workspace'))
if os.path.exists('/workspace/output'):
    print("Output:", os.listdir('/workspace/output'))
else:
    print("Output directory does not exist")