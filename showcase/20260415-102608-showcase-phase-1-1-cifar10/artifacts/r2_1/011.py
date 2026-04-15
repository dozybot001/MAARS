import os
import torch

# Search everywhere
def find_all(name):
    for root, dirs, files in os.walk('/'):
        if name in files:
            yield os.path.join(root, name)

print("Searching for source_badnets.pth...")
for p in find_all('source_badnets.pth'):
    print(p)

print("\nChecking CIFAR-100 data...")
if os.path.exists('/workspace/data/cifar-100-python'):
    print("CIFAR-100 exists")
    print(os.listdir('/workspace/data/cifar-100-python'))