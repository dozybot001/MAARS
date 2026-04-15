import os
for root, dirs, files in os.walk('/workspace'):
    for f in files:
        if f.endswith('.pth'):
            print(os.path.join(root, f))