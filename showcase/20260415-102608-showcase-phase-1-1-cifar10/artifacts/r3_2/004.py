import torch

state_dict = torch.load('/workspace/artifacts/r3_1/diff_lr_ft_model.pth', map_location='cpu')
print(f"fc.weight shape: {state_dict['fc.weight'].shape}")
print(f"fc.bias shape: {state_dict['fc.bias'].shape}")