import os
import torch
for i in [1, 2, 3]:
    p = f'/workspace/artifacts/{i}/source_badnets.pth'
    if os.path.exists(p):
        try:
            sd = torch.load(p, map_location='cpu')
            if 'fc.weight' in sd: shape = sd['fc.weight'].shape
            elif 'state_dict' in sd: shape = sd['state_dict']['fc.weight'].shape
            else: shape = "Unknown"
            print(f"Path {p} fc shape: {shape}")
        except:
            print(f"Failed to load {p}")
    else:
        print(f"Path {p} does not exist")