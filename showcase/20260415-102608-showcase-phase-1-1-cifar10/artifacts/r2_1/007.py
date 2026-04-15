import torch
for i in [1, 2, 3]:
    p = f'/workspace/artifacts/{i}/source_badnets.pth'
    if os.path.exists(p):
        sd = torch.load(p, map_location='cpu')
        if 'fc.weight' in sd: print(f"Path {p} classes: {sd['fc.weight'].shape[0]}")
        elif 'state_dict' in sd: print(f"Path {p} classes: {sd['state_dict']['fc.weight'].shape[0]}")