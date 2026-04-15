import torch
sd = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')
print(f"conv1.weight shape: {sd['conv1.weight'].shape}")