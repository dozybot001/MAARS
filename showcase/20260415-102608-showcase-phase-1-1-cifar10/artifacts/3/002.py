import os
import glob

print("Listing all files in /workspace/data/ recursively:")
for root, dirs, files in os.walk('/workspace/data/'):
    for file in files:
        print(os.path.join(root, file))

# Also check for torchvision datasets location
import torchvision
print("Torchvision version:", torchvision.__version__)