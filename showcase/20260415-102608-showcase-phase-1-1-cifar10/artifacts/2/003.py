import torch

state_dict = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')
print(list(state_dict.keys())[:10])
print(state_dict['conv1.weight'].shape)