import torch
p = '/workspace/artifacts/3/full_ft_model.pth'
if os.path.exists(p):
    sd = torch.load(p, map_location='cpu')
    if 'fc.weight' in sd: print(f"Classes: {sd['fc.weight'].shape[0]}")
    elif 'state_dict' in sd: print(f"Classes: {sd['state_dict']['fc.weight'].shape[0]}")