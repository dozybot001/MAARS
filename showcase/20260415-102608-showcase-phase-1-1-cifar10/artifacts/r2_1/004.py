import torch
model_path = '/workspace/artifacts/1/source_badnets.pth'
checkpoint = torch.load(model_path, map_location='cpu')
if 'fc.weight' in checkpoint:
    print(f"fc.weight shape: {checkpoint['fc.weight'].shape}")
elif 'state_dict' in checkpoint and 'fc.weight' in checkpoint['state_dict']:
    print(f"fc.weight shape: {checkpoint['state_dict']['fc.weight'].shape}")