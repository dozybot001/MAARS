import torch
checkpoint = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')
if 'fc.weight' in checkpoint:
    print(f"fc.weight shape: {checkpoint['fc.weight'].shape}")
elif 'classifier.weight' in checkpoint:
    print(f"classifier.weight shape: {checkpoint['classifier.weight'].shape}")
else:
    for k, v in checkpoint.items():
        if 'fc' in k or 'classifier' in k:
            print(f"{k} shape: {v.shape}")