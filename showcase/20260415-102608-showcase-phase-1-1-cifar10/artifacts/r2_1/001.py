import os
import torch
import torch.nn as nn
from torchvision import models, datasets, transforms
import json

def find_file(name, search_path='/workspace'):
    results = []
    for root, dirs, files in os.walk(search_path):
        if name in files:
            results.append(os.path.join(root, name))
    return results

source_paths = find_file('source_badnets.pth')
print(f"Model paths: {source_paths}")

# Check artifacts from r1_1 which might contain the source model and trigger info
r1_1_path = '/workspace/artifacts/r1_1'
if os.path.exists(r1_1_path):
    print(f"Contents of {r1_1_path}: {os.listdir(r1_1_path)}")

# Check data
print(f"Contents of /workspace/data: {os.listdir('/workspace/data')}")